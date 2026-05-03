# TypeRelay

A simulated typing tool for noVNC and remote consoles.

TypeRelay turns pasted text into real keystrokes when paste support is blocked or unreliable. It is aimed at Windows users who need to type long commands, credentials, setup scripts, or configuration blocks into noVNC and similar remote console surfaces.

## Features

- Paste or load long text from a file
- Configurable countdown before typing starts
- Adjustable per-key interval and extra newline pause
- Global `F2` emergency stop during countdown or typing
- Polished desktop UI built with Tkinter and `ttkbootstrap`
- Single-file Windows `.exe` build from GitHub Actions

## How It Works

1. Paste text into the editor or load a text file.
2. Set the countdown and timing values.
3. Click `Start Typing`.
4. Switch focus to your noVNC session before the countdown ends.
5. TypeRelay simulates the keystrokes into the active window.
6. Press global `F2` at any time during countdown or typing to stop the current run.

## Run From Source

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
python -m typerelay
```

## Build A Single-File EXE Locally

```powershell
pyinstaller --noconfirm --onefile --windowed --paths src --name TypeRelay src/typerelay/__main__.py
```

The built executable will be written to `dist/TypeRelay.exe`.

## Download The EXE From GitHub Actions

Every push and pull request runs the Windows build workflow:

1. Open the latest workflow run in GitHub Actions.
2. Download the `TypeRelay-windows-exe` artifact.
3. Extract the artifact and run `TypeRelay.exe`.

## Timing Notes

- `Countdown` is how long TypeRelay waits before sending the first key.
- `Key interval` is the delay between typed characters.
- `Newline pause` adds extra delay after `Enter`.

If noVNC misses characters, raise the timing values slightly and try again.

## Hotkey Behavior

- `F2` is global.
- `F2` only stops an active run.
- `F2` does nothing while the app is idle, which helps avoid accidental starts.

## Troubleshooting

### The global `F2` hotkey does not work

Try running the app as Administrator. Some Windows environments block low-level keyboard hooks for non-elevated processes.

### The wrong window receives the text

Use a longer countdown and make sure the noVNC console has focus before typing begins.

### noVNC misses characters

Increase `Key interval` and `Newline pause`. Remote consoles often need slower input than local desktop apps.

### Chinese or IME-based text behaves inconsistently

TypeRelay is most reliable for ASCII-heavy terminal input such as commands, URLs, tokens, configuration lines, and passwords. IME-driven characters depend on the active keyboard/input method and may not reproduce exactly in all remote sessions.

### Antivirus flags the EXE

Single-file executables created by PyInstaller are sometimes treated cautiously by antivirus tools. If needed, build the binary yourself from source or use a repository release artifact you trust.

## Repository Layout

```text
src/typerelay/
  app.py
  hotkeys.py
  theme.py
  typing_engine.py
tests/
.github/workflows/build.yml
```

## License

No license file is included yet. Add one before public distribution if you want reuse terms to be explicit.
