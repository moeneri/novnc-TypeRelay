from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from tkinter import END, Text, filedialog, messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, LEFT, RIGHT, X

from typerelay.hotkeys import register_stop_hotkey, resolve_hotkey_action, unregister_stop_hotkey
from typerelay.theme import PALETTE, STATUS_STYLES
from typerelay.typing_engine import (
    TypingCancelledError,
    build_key_actions,
    count_effective_keys,
    type_actions,
)


class PyAutoGUIEmitter:
    def __init__(self) -> None:
        import pyautogui

        pyautogui.FAILSAFE = True
        self._pyautogui = pyautogui

    def write_text(self, text: str, interval: float) -> None:
        self._pyautogui.write(text, interval=interval)

    def press_key(self, key: str) -> None:
        self._pyautogui.press(key)


class TypeRelayApp:
    def __init__(self, root: ttk.Window) -> None:
        self.root = root
        self.root.title("TypeRelay")
        self.root.geometry("1024x720")
        self.root.minsize(900, 640)

        self.countdown_var = ttk.StringVar(value="3")
        self.interval_var = ttk.StringVar(value="0.03")
        self.newline_pause_var = ttk.StringVar(value="0.12")
        self.status_var = ttk.StringVar(value="Paste your text, tune the timing, and start when ready.")
        self.mode_var = ttk.StringVar(value="Ready")
        self.meta_var = ttk.StringVar(value="0 actions queued")
        self.hotkey_var = ttk.StringVar(value="Global Hotkey: F2 stops the active run")

        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._ui_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._hotkey_handle: object | None = None

        self._build_ui()
        self._register_hotkey()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(120, self._poll_ui_queue)

    def _build_ui(self) -> None:
        self.root.configure(bg=PALETTE["bg"])

        shell = ttk.Frame(self.root, padding=18, bootstyle="light")
        shell.pack(fill=BOTH, expand=True)

        self.header_card = ttk.Frame(shell, padding=18, bootstyle="light")
        self.header_card.pack(fill=X)

        title_col = ttk.Frame(self.header_card, bootstyle="light")
        title_col.pack(side=LEFT, fill=X, expand=True)

        ttk.Label(
            title_col,
            text="TypeRelay",
            font=("Segoe UI Semibold", 22),
            bootstyle="dark",
        ).pack(anchor="w")
        ttk.Label(
            title_col,
            text="Simulated typing for noVNC and remote consoles.",
            font=("Segoe UI", 10),
            bootstyle="secondary",
        ).pack(anchor="w", pady=(4, 0))

        self.status_badge = ttk.Label(
            self.header_card,
            text=self.mode_var.get(),
            padding=(14, 8),
            font=("Segoe UI Semibold", 10),
            bootstyle="secondary",
        )
        self.status_badge.pack(side=RIGHT)

        body = ttk.Frame(shell, padding=(0, 18, 0, 0), bootstyle="light")
        body.pack(fill=BOTH, expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        editor_card = ttk.Labelframe(body, text="Input", padding=16, bootstyle="light")
        editor_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        editor_card.rowconfigure(0, weight=1)
        editor_card.columnconfigure(0, weight=1)

        text_wrap = ttk.Frame(editor_card, bootstyle="light")
        text_wrap.grid(row=0, column=0, sticky="nsew")
        text_wrap.rowconfigure(0, weight=1)
        text_wrap.columnconfigure(0, weight=1)

        self.text_box = Text(
            text_wrap,
            wrap="word",
            undo=True,
            font=("Cascadia Code", 11),
            padx=14,
            pady=14,
            relief="flat",
            background=PALETTE["card"],
            foreground=PALETTE["ink"],
            insertbackground=PALETTE["accent"],
        )
        self.text_box.grid(row=0, column=0, sticky="nsew")
        self.text_box.bind("<<Modified>>", self._on_text_modified)

        scrollbar = ttk.Scrollbar(text_wrap, orient="vertical", command=self.text_box.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text_box.configure(yscrollcommand=scrollbar.set)

        editor_footer = ttk.Frame(editor_card, bootstyle="light")
        editor_footer.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        ttk.Label(editor_footer, textvariable=self.meta_var, bootstyle="secondary").pack(side=LEFT)
        ttk.Label(editor_footer, text="ASCII-heavy terminal input is the most reliable.", bootstyle="secondary").pack(
            side=RIGHT
        )

        side = ttk.Frame(body, bootstyle="light")
        side.grid(row=0, column=1, sticky="nsew")
        side.rowconfigure(2, weight=1)

        controls_card = ttk.Labelframe(side, text="Timing", padding=16, bootstyle="light")
        controls_card.grid(row=0, column=0, sticky="ew")
        controls_card.columnconfigure(1, weight=1)

        self._build_field(controls_card, 0, "Countdown (seconds)", self.countdown_var)
        self._build_field(controls_card, 1, "Key interval (seconds)", self.interval_var)
        self._build_field(controls_card, 2, "Newline pause (seconds)", self.newline_pause_var)

        actions_card = ttk.Labelframe(side, text="Actions", padding=16, bootstyle="light")
        actions_card.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        actions_card.columnconfigure((0, 1), weight=1)

        self.start_button = ttk.Button(
            actions_card,
            text="Start Typing",
            command=self.start_typing,
            bootstyle="success",
        )
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))

        self.stop_button = ttk.Button(
            actions_card,
            text="Stop Now",
            command=self.request_stop,
            bootstyle="danger",
            state="disabled",
        )
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=(0, 8))

        ttk.Button(actions_card, text="Load File", command=self.load_text_file, bootstyle="info").grid(
            row=1, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(actions_card, text="Clear", command=self.clear_text, bootstyle="secondary").grid(
            row=1, column=1, sticky="ew", padx=(6, 0)
        )

        notes_card = ttk.Labelframe(side, text="Run Notes", padding=16, bootstyle="light")
        notes_card.grid(row=2, column=0, sticky="nsew", pady=(12, 0))

        notes = [
            "1. Paste or load the full text here.",
            "2. Click Start Typing, then focus your noVNC session.",
            "3. TypeRelay minimizes during countdown so the target can take focus.",
            "4. Press global F2 any time during countdown or typing to stop the run.",
        ]
        for line in notes:
            ttk.Label(notes_card, text=line, bootstyle="secondary", wraplength=300, justify="left").pack(
                anchor="w", pady=(0, 6)
            )

        footer = ttk.Frame(shell, padding=(0, 14, 0, 0), bootstyle="light")
        footer.pack(fill=X)
        ttk.Label(footer, textvariable=self.status_var, bootstyle="dark").pack(side=LEFT)
        ttk.Label(footer, textvariable=self.hotkey_var, bootstyle="secondary").pack(side=RIGHT)

    def _build_field(self, parent: ttk.Widget, row: int, label: str, variable: ttk.StringVar) -> None:
        ttk.Label(parent, text=label, bootstyle="dark").grid(row=row, column=0, sticky="w", pady=(0, 10), padx=(0, 12))
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=(0, 10))

    def _register_hotkey(self) -> None:
        result, handle = register_stop_hotkey(self.request_stop_from_hotkey)
        self._hotkey_handle = handle
        self.hotkey_var.set(result.message if result.ok else f"{result.message} Try running as administrator.")

    def _on_text_modified(self, _event=None) -> None:
        self.text_box.edit_modified(False)
        self.meta_var.set(f"{count_effective_keys(self.current_text())} actions queued")

    def current_text(self) -> str:
        text = self.text_box.get("1.0", END)
        return text[:-1] if text.endswith("\n") else text

    def is_running(self) -> bool:
        return bool(self._worker and self._worker.is_alive())

    def request_stop_from_hotkey(self) -> None:
        if resolve_hotkey_action(is_running=self.is_running()) == "stop":
            self.request_stop()

    def request_stop(self) -> None:
        if not self.is_running():
            return
        self._stop_event.set()
        self._ui_queue.put(("mode", "Stopped"))
        self._ui_queue.put(("status", "Stop requested. Waiting for the current keystroke to finish."))

    def clear_text(self) -> None:
        self.text_box.delete("1.0", END)
        self.meta_var.set("0 actions queued")
        self.status_var.set("Input cleared.")

    def load_text_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select a text file",
            filetypes=[
                ("Text files", "*.txt *.md *.log *.cfg *.ini *.json *.yaml *.yml *.csv"),
                ("All files", "*.*"),
            ],
        )
        if not file_path:
            return

        try:
            text = Path(file_path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = Path(file_path).read_text(encoding="gb18030")
        except OSError as exc:
            messagebox.showerror("Unable to read file", str(exc))
            return

        self.text_box.delete("1.0", END)
        self.text_box.insert("1.0", text)
        self.meta_var.set(f"{count_effective_keys(self.current_text())} actions queued")
        self.status_var.set(f"Loaded {Path(file_path).name}.")

    def start_typing(self) -> None:
        if self.is_running():
            messagebox.showinfo("Run in progress", "Wait for the current run to finish or stop it with F2.")
            return

        text = self.current_text()
        if not text:
            messagebox.showwarning("No text loaded", "Paste or load the text you want to type first.")
            return

        try:
            countdown = float(self.countdown_var.get())
            interval = float(self.interval_var.get())
            newline_pause = float(self.newline_pause_var.get())
        except ValueError:
            messagebox.showerror("Invalid timing value", "Countdown and delays must be numeric values.")
            return

        if countdown < 0 or interval < 0 or newline_pause < 0:
            messagebox.showerror("Invalid timing value", "Timing values must be zero or greater.")
            return

        actions = build_key_actions(text)
        self._stop_event.clear()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self._set_mode("Countdown")
        self.status_var.set(f"Preparing to send {len(actions)} actions. Focus noVNC before the countdown ends.")
        self.root.iconify()

        self._worker = threading.Thread(
            target=self._run_typing_job,
            args=(actions, countdown, interval, newline_pause),
            daemon=True,
        )
        self._worker.start()

    def _run_typing_job(
        self,
        actions: list,
        countdown: float,
        interval: float,
        newline_pause: float,
    ) -> None:
        try:
            self._countdown(countdown)
            emitter = PyAutoGUIEmitter()

            def on_progress(done: int, total: int) -> None:
                self._ui_queue.put(("progress", (done, total)))

            self._ui_queue.put(("mode", "Typing"))
            self._ui_queue.put(("status", "Typing into the active window now."))
            type_actions(
                actions,
                emitter,
                interval=interval,
                newline_pause=newline_pause,
                stop_requested=self._stop_event.is_set,
                on_progress=on_progress,
            )
        except TypingCancelledError:
            self._ui_queue.put(("mode", "Stopped"))
            self._ui_queue.put(("status", "Run stopped. You can adjust the text and try again."))
        except ImportError as exc:
            self._ui_queue.put(("mode", "Error"))
            self._ui_queue.put(("error", f"Missing dependency: {exc}. Install requirements and relaunch."))
        except Exception as exc:
            self._ui_queue.put(("mode", "Error"))
            self._ui_queue.put(("error", f"Typing failed: {exc}"))
        else:
            self._ui_queue.put(("mode", "Done"))
            self._ui_queue.put(("status", "Typing completed successfully."))
        finally:
            self._ui_queue.put(("finish", None))

    def _countdown(self, countdown: float) -> None:
        whole_seconds = int(countdown)
        remainder = countdown - whole_seconds
        for remaining in range(whole_seconds, 0, -1):
            if self._stop_event.is_set():
                raise TypingCancelledError("Stop requested during countdown.")
            self._ui_queue.put(("mode", "Countdown"))
            self._ui_queue.put(("status", f"Starting in {remaining} second(s). Focus the target window now."))
            time.sleep(1)

        if remainder > 0:
            if self._stop_event.is_set():
                raise TypingCancelledError("Stop requested during countdown.")
            self._ui_queue.put(("status", "Starting..."))
            time.sleep(remainder)

    def _set_mode(self, mode: str) -> None:
        self.mode_var.set(mode)
        style = STATUS_STYLES.get(mode, {"bootstyle": "secondary"})
        self.status_badge.configure(text=mode, bootstyle=style["bootstyle"])

    def _poll_ui_queue(self) -> None:
        while True:
            try:
                kind, payload = self._ui_queue.get_nowait()
            except queue.Empty:
                break

            if kind == "mode":
                self._set_mode(str(payload))
            elif kind == "status":
                self.status_var.set(str(payload))
            elif kind == "progress":
                done, total = payload
                self.meta_var.set(f"{done}/{total} actions sent")
            elif kind == "error":
                self.status_var.set(str(payload))
                messagebox.showerror("TypeRelay", str(payload))
            elif kind == "finish":
                self.start_button.configure(state="normal")
                self.stop_button.configure(state="disabled")
                self.root.deiconify()
                self.root.lift()

        self.root.after(120, self._poll_ui_queue)

    def on_close(self) -> None:
        self._stop_event.set()
        unregister_stop_hotkey(self._hotkey_handle)
        self.root.destroy()


def main() -> int:
    root = ttk.Window(themename="flatly")
    app = TypeRelayApp(root)
    app.meta_var.set(f"{count_effective_keys(app.current_text())} actions queued")
    root.mainloop()
    return 0
