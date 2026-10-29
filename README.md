# rui-plugin-template

Minimal, MIT-licensed starting point for a **RUI device plugin**: one manifest, one
device manifest, one adapter skeleton, and the official contract check. Clone it,
rename it, replace the placeholders with your device's I/O — no fork of the RUI core.

`rui-plugin-template` 是 **RUI 设备插件**的最小 MIT 模板：插件清单 + 设备清单 +
`DeviceAdapter` 骨架 + 官方契约检查。clone 后改成自己的设备即可，**不需要 fork
RUI 核心**。

---

## 中文

### 1. 快速开始

```bash
git clone https://github.com/yes999zc/rui-plugin-template.git
cd rui-plugin-template
python -m venv .venv
. .venv/bin/activate
pip install pytest
```

仓库内容：

| 路径 | 作用 |
|---|---|
| `plugin.yaml` | 插件元数据：id、版本、`rui_compat` 兼容窗口、信任级别、设备清单列表 |
| `devices/example.yaml` | 一个设备型号：transport、capabilities、`runtime.entrypoint`、向导参数 |
| `adapter.py` | `DeviceAdapter` 全部方法的骨架；每个方法有 TODO（做什么/返回什么/对应契约哪段） |
| `tests/test_contract.py` | 一条契约测试：调用官方 checker 跑本仓，断言 exit 0 |
| `LICENSE` | MIT |

### 2. 本地验证

先拿到一份 RUI 核心（本模板与它同目录）：

```bash
git clone https://github.com/yes999zc/rui.git ../house-ear
pip install -e ../house-ear
```

然后跑官方契约工具（三选一）：

```bash
# 已发布 CLI（优先）
rui-adapter-check --adapter .

# 当前核心已有的等价入口（manifest + adapter 冒烟）
rui plug-test . --adapter ./adapter.py:build

# 只验清单、不加载 adapter
rui plug-test .
```

再跑模板自带的契约测试（`rui-adapter-check` 尚未合入时会 **skip** 并打印上面的
替代命令，不会假绿）：

```bash
python -m pytest tests/ -q
```

### 3. 改成自己的设备

1. `plugin.yaml`：改 `id`、`name`、`version`、`maintainer`、`homepage`。`rui_compat`
   保持 dual-window：下界 = 你真正测过的第一个核心版本，上界 = 已测过的下一个 minor
   （本模板写 `>=0.8.1 <0.9.0`）。`trust: trusted` 表示 adapter 在 RUI 进程内运行
   （完整权限），只给自己的代码用；第三方发布请改 `sidecar` 并配 `runtime.image`。
2. `devices/example.yaml`：改 `id`/`model`/`vendor`/`transport`/`protocol`/
   `capabilities`/`params`；`runtime.entrypoint` 指向你的 `模块:函数`；
   `runtime.listen_port` 是设备回连端口（按你的设备改，不要和同机其它插件撞）；
   `token_env` 只写**环境变量名**，永远不要把 token 写进仓库。
3. `adapter.py`：按 TODO 替换 `probe` / `open` / `close` / `frames` / `play` /
   `stop_playback` / `set_volume` / `read_volume` / `set_led` / `drain_signals` /
   `drain_wakes`。`probe()` 报的 `channels` 必须等于 `mic_channels + ref_channels`，
   能力要与清单一致（否则 RUI 会降级并在契约报告里 WARN）。
4. 重新跑第 2 步；全 PASS/SUCCESS 后再提交。

### 4. 起一个最小 RUI 服务

新建 `config.yaml`（与仓库同目录的示例，**不要提交真实地址/凭据**）：

```yaml
devices:
  - id: example
    adapter: example-plugin      # 必须等于 plugin.yaml 的 id
    host: <your-device-host>     # 你的设备地址/局域网名（inbound 下用于显示/诊断）
    room: Example room
```

把插件目录挂载给 RUI，然后起服务：

```bash
export RUI_CONFIG=./config.yaml
# runtime.token_env 指向的环境变量：由你写入设备 token（不要写进命令历史/仓库）
read -rs RUI_DEVICE_TOKEN && export RUI_DEVICE_TOKEN
rui serve
```

打开 RUI 控制台，设备应出现并处于 connected；`/api/v1/plugs` 能看到
`example-plugin`。

### 5. 契约检查现在能保证什么

- **manifest 层**：schema/字段/路径/`rui_compat`/capability 词表/`trust` 与
  `runtime.mode` 的一致性（只读，不执行代码）。
- **adapter 冒烟**：懒加载 `entrypoint`，用 fake device 跑 probe、帧、播放、事件轮询、
  幂等 close；不测 ASR/LLM/TTS，也不替代真机验收。
- 真机仍需你自己验：真实采集/播放、掉线重连、音量/LED、设备侧 token 校验。

---

## English

### 1. Quick start

```bash
git clone https://github.com/yes999zc/rui-plugin-template.git
cd rui-plugin-template
python -m venv .venv
. .venv/bin/activate
pip install pytest
```

What you get:

| Path | Purpose |
|---|---|
| `plugin.yaml` | Plugin metadata: id, version, `rui_compat` window, trust level, device files |
| `devices/example.yaml` | One device model: transport, capabilities, `runtime.entrypoint`, wizard params |
| `adapter.py` | The full `DeviceAdapter` surface with a TODO per method |
| `tests/test_contract.py` | One contract check: run the official checker, assert exit 0 |
| `LICENSE` | MIT |

### 2. Validate locally

Check out the RUI core next to this repo, then install it:

```bash
git clone https://github.com/yes999zc/rui.git ../house-ear
pip install -e ../house-ear
```

Run the official contract tooling:

```bash
# Preferred once the CLI ships
rui-adapter-check --adapter .

# Equivalent entry point available in the core today
rui plug-test . --adapter ./adapter.py:build

# Manifest only, no adapter import
rui plug-test .
```

Then run the bundled contract test (it **skips** with those exact commands while
`rui-adapter-check` is still being merged, so a fresh clone is never falsely red):

```bash
python -m pytest tests/ -q
```

### 3. Make it your device

1. `plugin.yaml`: change `id`, `name`, `version`, `maintainer`, `homepage`. Keep
   `rui_compat` as a dual window: lower bound = the first core release you tested,
   upper bound = the next minor you have tested (`>=0.8.1 <0.9.0` here).
   `trust: trusted` means the adapter runs **in-process** with full RUI privileges;
   only use it for code you control. Third-party distributions should use `sidecar`
   with `runtime.image`.
2. `devices/example.yaml`: change `id`/`model`/`vendor`/`transport`/`protocol`/
   `capabilities`/`params`; point `runtime.entrypoint` at your `module:function`;
   set `runtime.listen_port` to your device's dial-back port; `token_env` is only
   the **name** of an environment variable — never commit a token.
3. `adapter.py`: replace the TODOs in `probe` / `open` / `close` / `frames` / `play` /
   `stop_playback` / `set_volume` / `read_volume` / `set_led` / `drain_signals` /
   `drain_wakes`. `probe().channels` must equal `mic_channels + ref_channels`, and
   the reported capabilities must match the manifest (otherwise RUI degrades and
   the contract report warns).
4. Re-run step 2. Only ship after every check is PASS/WARN/SKIP for the right
   reason.

### 4. Start a minimal RUI service

Create `config.yaml` (keep real hosts/credentials out of the repo):

```yaml
devices:
  - id: example
    adapter: example-plugin      # must equal plugin.yaml's id
    host: <your-device-host>
    room: Example room
```

Point RUI at it and start the control plane:

```bash
export RUI_CONFIG=./config.yaml
# The env var named by runtime.token_env; set it without writing the secret to disk.
read -rs RUI_DEVICE_TOKEN && export RUI_DEVICE_TOKEN
rui serve
```

The device should appear in the RUI console as connected, and `/api/v1/plugs`
should list `example-plugin`.

### 5. What the contract check does — and does not — prove

- **Manifest layer**: schema/fields/path escapes/`rui_compat`/capability vocabulary/
  `trust` vs `runtime.mode` consistency. Read-only; it never executes your code.
- **Adapter smoke**: lazily imports the entry point and runs probe, capture frames,
  playback, event polls and an idempotent close against a fake device. It is not an
  ASR/LLM/TTS test and it does not replace real-device acceptance.
- You still validate on hardware: real capture/playback, reconnect behaviour,
  volume/LED, and device-side token checks.

---

## License

MIT — see [LICENSE](LICENSE). Reference contract: `docs/socket-plug-v1.md` in
<https://github.com/yes999zc/rui>.
