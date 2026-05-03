# TypeRelay

A simulated typing tool for noVNC and remote consoles.  
一个用于 noVNC 和远程控制台的模拟输入工具。

TypeRelay turns pasted text into real keystrokes when paste support is blocked or unreliable. It is aimed at Windows users who need to type long commands, credentials, setup scripts, or configuration blocks into noVNC and similar remote console surfaces.  
TypeRelay 会在粘贴不可用或不稳定时，将文本转换为真实键盘输入。它面向需要在 noVNC 和类似远程控制台中输入长命令、凭据、安装脚本或配置内容的 Windows 用户。

## 功能 Features

- Paste or load long text from a file
- Configurable countdown before typing starts
- Adjustable per-key interval and extra newline pause
- Global `F2` emergency stop during countdown or typing
- Polished desktop UI built with Tkinter and `ttkbootstrap`
- Single-file Windows `.exe` build from GitHub Actions
- 支持直接粘贴长文本或从文件导入
- 支持设置倒计时、按键间隔和换行停顿
- 倒计时或输入过程中可使用全局 `F2` 紧急停止
- 使用 Tkinter 与 `ttkbootstrap` 构建更完整的桌面界面
- GitHub Actions 可自动生成 Windows 单文件 `.exe`

## 运行方式 How It Works

1. Paste text into the editor or load a text file.
2. Set the countdown and timing values.
3. Click `Start Typing`.
4. Switch focus to your noVNC session before the countdown ends.
5. TypeRelay simulates the keystrokes into the active window.
6. Press global `F2` at any time during countdown or typing to stop the current run.
1. 将文本粘贴到编辑区，或导入一个文本文件。
2. 设置倒计时和输入延迟参数。
3. 点击 `Start Typing` / `开始输入`。
4. 在倒计时结束前切换到 noVNC 会话。
5. TypeRelay 会向当前活动窗口模拟键盘输入。
6. 在倒计时或输入过程中，随时按全局 `F2` 停止当前任务。

## 软件语言 Software Language

- The application automatically detects the system language at startup.
- Chinese systems default to Simplified Chinese.
- Other systems default to English.
- The current version does not add a manual language switch yet.
- 程序启动时会自动识别系统语言。
- 系统语言为中文时，界面默认显示简体中文。
- 其他系统语言默认显示英文。
- 当前版本暂未加入手动切换语言按钮。

## 从源码运行 Run From Source

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
python -m typerelay
```

## 本地构建单文件 EXE Build A Single-File EXE Locally

```powershell
pyinstaller --noconfirm --onefile --windowed --paths src --name TypeRelay src/typerelay/__main__.py
```

The built executable will be written to `dist/TypeRelay.exe`.  
构建完成后的可执行文件位于 `dist/TypeRelay.exe`。

## 从 GitHub Actions 下载 EXE Download The EXE From GitHub Actions

Every push and pull request runs the Windows build workflow:
1. Open the latest workflow run in GitHub Actions.
2. Download the `TypeRelay-windows-exe` artifact.
3. Extract the artifact and run `TypeRelay.exe`.
每次 push 或 pull request 都会触发 Windows 构建流程：
1. 打开最新的 GitHub Actions 工作流运行记录。
2. 下载 `TypeRelay-windows-exe` artifact。
3. 解压后直接运行 `TypeRelay.exe`。

## 时间参数说明 Timing Notes

- `Countdown` is how long TypeRelay waits before sending the first key.
- `Key interval` is the delay between typed characters.
- `Newline pause` adds extra delay after `Enter`.
If noVNC misses characters, raise the timing values slightly and try again.
- `Countdown` 表示开始发送第一个按键前的等待时间。
- `Key interval` 表示普通字符之间的延迟。
- `Newline pause` 表示在发送 `Enter` 后额外等待的时间。
- 如果 noVNC 漏字，适当增加这些时间值再重试。

## 热键说明 Hotkey Behavior

- `F2` is global.
- `F2` only stops an active run.
- `F2` does nothing while the app is idle, which helps avoid accidental starts.
- `F2` 是全局热键。
- `F2` 只会停止正在执行的任务。
- 程序空闲时按 `F2` 不会启动输入，能避免误触。

## 故障排查 Troubleshooting

### The global `F2` hotkey does not work / 全局 `F2` 无法工作

Try running the app as Administrator. Some Windows environments block low-level keyboard hooks for non-elevated processes.
尝试以管理员身份运行程序。某些 Windows 环境会阻止普通权限进程注册底层键盘钩子。

### The wrong window receives the text / 文本输入到了错误窗口

Use a longer countdown and make sure the noVNC console has focus before typing begins.
请延长倒计时，并确认在输入开始前 noVNC 控制台已经获得焦点。

### noVNC misses characters / noVNC 漏字

Increase `Key interval` and `Newline pause`. Remote consoles often need slower input than local desktop apps.
提高 `Key interval` 和 `Newline pause`。远程控制台通常比本地桌面程序更需要较慢的输入节奏。

### Chinese or IME-based text behaves inconsistently / 中文或输入法文本表现不稳定

TypeRelay is most reliable for ASCII-heavy terminal input such as commands, URLs, tokens, configuration lines, and passwords. IME-driven characters depend on the active keyboard/input method and may not reproduce exactly in all remote sessions.
TypeRelay 对以 ASCII 为主的终端输入最稳定，例如命令、URL、令牌、配置行和密码。依赖输入法的字符输入会受当前键盘/输入法影响，在不同远程会话中的表现可能不完全一致。

### Antivirus flags the EXE / 杀毒软件提示风险

Single-file executables created by PyInstaller are sometimes treated cautiously by antivirus tools. If needed, build the binary yourself from source or use a repository release artifact you trust.
PyInstaller 生成的单文件可执行程序有时会被杀毒软件谨慎对待。如有需要，可以自行从源码构建，或仅使用你信任的仓库产物。

## 仓库结构 Repository Layout

```text
src/typerelay/
  app.py
  i18n.py
  hotkeys.py
  theme.py
  typing_engine.py
tests/
.github/workflows/build.yml
```

## 仓库描述建议 Suggested Repository Description

`A simulated typing tool for noVNC and remote consoles. | 一个用于 noVNC 和远程控制台的模拟输入工具。`

