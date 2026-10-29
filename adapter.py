"""Minimal RUI device adapter skeleton (Socket & Plug v1).

Mounted by RUI at the entry point in ``devices/example.yaml``:
``runtime.entrypoint: "adapter:build"``. RUI imports this module lazily, calls
``build(device, config)`` once per configured device, then drives the resulting
object through the :class:`rui.device.contract.DeviceAdapter` protocol.

Everything here is deliberately in-memory: the template runs and passes
``rui plug-test . --adapter ./adapter.py:build`` on a laptop without a speaker.
Replace each ``TODO`` with your device's I/O. The contract is documented in
``rui/device/contract.py`` and ``docs/socket-plug-v1.md`` in the core repo.

Do not import device SDKs at module import time: RUI resolves the manifest
without executing the adapter, and the adapter is only imported when the device
plane starts. Keep slow/network setup in ``open()``, not at import.
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator

from rui.device.contract import (
    AudioFrame,
    Capability,
    DeviceInfo,
    DeviceServices,
    NullServices,
    Transport,
    percent_to_device_volume,
)

# Capture wire format advertised by probe(). Replace with your hardware's facts
# (the manifest may also declare them under devices[].audio_defaults).
FRAME_MS = 20
SAMPLE_RATE = 16_000
MIC_CHANNELS = 1


class ExampleAdapter:
    """A runnable placeholder implementing the whole DeviceAdapter surface.

    The in-memory `played` list and synthetic silence frames exist only so the
    contract kit can verify the surface without hardware. They are not a
    reference implementation of playback or capture.
    """

    #: Shell/mixer/light. This example device has none, so it uses NullServices
    #: and declares no volume/led capability in the manifest. If your device has
    #: a mixer or a light ring, assign a vendor object here and add the matching
    #: capability to devices/*.yaml.
    services: DeviceServices = NullServices()

    def __init__(self, device_id: str = "example-speaker", config: object | None = None) -> None:
        self._device_id = device_id
        self._config = config
        self._open = False
        self._seq = 0
        self._volume_percent = 50
        self._led = "off"
        #: Fake playback sink. rui plug-test checks that play() reached it; a real
        #: adapter replaces this with a socket/pipeline write.
        self.played: list[bytes] = []

    # ------------------------------------------------------------------ lifecycle
    async def probe(self) -> DeviceInfo:
        """Return what the device is, without opening a stream.

        Contract: ``DeviceAdapter.probe`` — returns :class:`DeviceInfo`.
        TODO: report the real model/transport/capabilities and the capture
        layout. ``channels`` must equal ``mic_channels + ref_channels``; keep
        the reported capabilities equal to (or a subset of) the manifest, or
        RUI degrades and the contract kit reports a WARN.
        """
        return DeviceInfo(
            id=self._device_id,
            adapter="example-plugin",
            model="EXAMPLE-01",
            host="",  # TODO: fill from device params (e.g. params["host"])
            room="",
            capabilities=frozenset({Capability.PLAYBACK}),
            transport=Transport.INBOUND,
            channels=MIC_CHANNELS,
            sample_rate=SAMPLE_RATE,
            bit_depth=16,
            mic_channels=MIC_CHANNELS,
            ref_channels=0,
        )

    async def open(self) -> None:
        """Start talking to the device; make it idempotent if you can.

        Contract: ``DeviceAdapter.open`` — async, returns None.
        TODO: open the socket / start the helper process / accept the inbound
        client. Raise on a real failure; RUI reports it as a device error and
        retries according to its supervisor policy.
        """
        self._open = True

    async def close(self) -> None:
        """Release everything open() acquired. Must be safe to call twice.

        Contract: ``DeviceAdapter.close`` — async, returns None. The contract kit
        calls it twice and then checks that ``drain_wakes()`` is empty.
        TODO: close sockets, join tasks, flush buffers. Never raise for an
        already-closed resource.
        """
        self._open = False

    # -------------------------------------------------------------------- capture
    async def frames(self) -> AsyncIterator[AudioFrame]:
        """Yield capture blocks until closed.

        Contract: ``DeviceAdapter.frames`` — async iterator of
        :class:`AudioFrame`; no I/O may run at import time.
        TODO: read a block from the microphone/socket, convert to signed 16-bit
        little-endian PCM, and set ``channels``/``sample_rate`` to match
        ``probe()``. Keep one block per ``FRAME_MS`` (or smaller) so the VAD/KWS
        sees continuous audio. ``ts_ms`` must be monotonic milliseconds.
        """
        if not self._open:
            raise RuntimeError("adapter is not open")

        samples = SAMPLE_RATE * FRAME_MS // 1000
        pcm = b"\x00" * (samples * MIC_CHANNELS * 2)  # silence; TODO: real capture
        while self._open:
            self._seq += 1
            yield AudioFrame(
                device_id=self._device_id,
                seq=self._seq,
                ts_ms=time.monotonic() * 1000.0,
                pcm=pcm,
                channels=MIC_CHANNELS,
                sample_rate=SAMPLE_RATE,
                reference_channels=0,
            )
            await asyncio.sleep(FRAME_MS / 1000.0)

    # ------------------------------------------------------------------- playback
    async def play(self, pcm: bytes, *, sample_rate: int, channels: int) -> None:
        """Hand one interleaved int16 PCM block to the speaker.

        Contract: ``DeviceAdapter.play`` — async, returns None; ``sample_rate``
        and ``channels`` describe THIS buffer (RUI already resampled it if the
        manifest asked for a different wire format).
        TODO: write ``pcm`` to the device sink. Respect back-pressure; a blocked
        sink stalls the reply, and RUI bounds the wait instead of buffering
        seconds of audio. The in-memory append below is a stand-in.
        """
        self.played.append(bytes(pcm))

    async def stop_playback(self, fade_ms: int = 120) -> None:
        """Silence the speaker now, including audio already buffered on it.

        Contract: ``DeviceAdapter.stop_playback`` — async, returns None.
        TODO: send your device's flush/stop command and wait for it to take
        effect (or at least for the command to be delivered). This is called on
        barge-in and before a reminder speaks, so a stale buffer must not
        survive it.
        """
        return None

    # --------------------------------------------------------------------- mixer
    async def set_volume(self, percent: int) -> None:
        """Set the device mixer from a 0-100 config/UI percentage.

        Contract: ``DeviceAdapter.set_volume`` — async, returns None. ``percent``
        must be an int in 0..100; reject (do not clamp) anything else.
        TODO: map to the device's own scale with
        :func:`percent_to_device_volume` and write it. Remove this method only
        together with the ``volume`` capability.
        """
        if isinstance(percent, bool) or not isinstance(percent, int):
            raise ValueError(f"volume percent must be an int in 0..100 (got {percent!r})")
        if not 0 <= percent <= 100:
            raise ValueError(f"volume percent must be in 0..100 (got {percent!r})")
        self._volume_percent = percent

    async def read_volume(self) -> int | None:
        """Return the device mixer value in 0-255, or None when it cannot report.

        Contract: ``DeviceAdapter.read_volume`` — async, returns ``int | None``.
        TODO: read the hardware mixer. Until then this derives the value from the
        last ``set_volume`` call, which is honest only for a device that has no
        independent volume buttons.
        """
        return percent_to_device_volume(self._volume_percent)

    # --------------------------------------------------------------------- light
    async def set_led(self, effect: str, color: str = "", *, repaint: bool = False) -> None:
        """Paint the light ring / status LED.

        Contract: ``DeviceAdapter.set_led`` — async, returns None.
        TODO: map ``effect`` (off/listening/thinking/speaking/...) to the device.
        ``repaint=True`` asks for a redraw of the current effect; it must never
        raise just because the ring is absent.
        """
        self._led = effect

    # ---------------------------------------------------------------- event polls
    def drain_signals(self) -> list:
        """Return vendor-assistant/key events since the last call.

        Contract: ``DeviceAdapter.drain_signals`` — SYNCHRONOUS, non-blocking,
        returns ``list``; default ``[]``. Must not do network/disk I/O. Events
        from the device's own assistant (not RUI's wake word) belong here.
        TODO: drain a bounded queue filled by your reader thread. Never return
        the same event twice.
        """
        return []

    def drain_wakes(self) -> list:
        """Return RUI wake words the device detected since the last call.

        Contract: ``DeviceAdapter.drain_wakes`` — SYNCHRONOUS, non-blocking,
        returns ``list[DeviceWake]``; default ``[]``. Only used when the
        manifest declares ``capability: device_wake`` and ``wake.source: device``
        (this template leaves wake on RUI KWS). Keep the queue bounded.
        TODO: return ``list[DeviceWake]`` with ``ts_ms`` on the same monotonic
        clock as ``AudioFrame.ts_ms``.
        """
        return []


def build(device: object | None = None, config: object | None = None) -> ExampleAdapter:
    """Construct the adapter for one configured device.

    ``runtime.entrypoint: "adapter:build"`` resolves here. ``device`` is the
    resolved device object from RUI's config (``device.id``, ``device.params``,
    ``device.room`` ...); ``config`` is the whole config. Both are optional so
    the contract kit can call ``build()``.
    TODO: pull host/credentials/params from ``device`` and pass them into your
    adapter. Never hard-code addresses or tokens in this file.
    """
    device_id = str(getattr(device, "id", "") or "example-speaker")
    return ExampleAdapter(device_id=device_id, config=config)
