from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from tkinter import END, Text, filedialog, messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, LEFT, RIGHT, X

from typerelay.hotkeys import register_stop_hotkey, resolve_hotkey_action, unregister_stop_hotkey
from typerelay.i18n import Localizer, build_localizer
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
    def __init__(self, root: ttk.Window, localizer: Localizer | None = None) -> None:
        self.root = root
        self.root.title("TypeRelay")
        self.root.geometry("1024x720")
        self.root.minsize(900, 640)
        self.l10n = localizer or build_localizer()

        self.countdown_var = ttk.StringVar(value="3")
        self.interval_var = ttk.StringVar(value="0.03")
        self.newline_pause_var = ttk.StringVar(value="0.12")
        self.status_var = ttk.StringVar(value=self.l10n.t("status.initial"))
        self.mode_var = ttk.StringVar(value="ready")
        self.meta_var = ttk.StringVar(value=self.l10n.t("meta.actions_queued", count=0))
        self.hotkey_var = ttk.StringVar(value=self.l10n.t("hotkey.ready"))

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
            text=self.l10n.t("app.tagline"),
            font=("Segoe UI", 10),
            bootstyle="secondary",
        ).pack(anchor="w", pady=(4, 0))

        self.status_badge = ttk.Label(
            self.header_card,
            text=self.l10n.t("mode.ready"),
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

        editor_card = ttk.Labelframe(body, text=self.l10n.t("panel.input"), padding=16, bootstyle="light")
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
        ttk.Label(editor_footer, text=self.l10n.t("meta.ascii_hint"), bootstyle="secondary").pack(
            side=RIGHT
        )

        side = ttk.Frame(body, bootstyle="light")
        side.grid(row=0, column=1, sticky="nsew")
        side.rowconfigure(2, weight=1)

        controls_card = ttk.Labelframe(side, text=self.l10n.t("panel.timing"), padding=16, bootstyle="light")
        controls_card.grid(row=0, column=0, sticky="ew")
        controls_card.columnconfigure(1, weight=1)

        self._build_field(controls_card, 0, self.l10n.t("label.countdown"), self.countdown_var)
        self._build_field(controls_card, 1, self.l10n.t("label.interval"), self.interval_var)
        self._build_field(controls_card, 2, self.l10n.t("label.newline_pause"), self.newline_pause_var)

        actions_card = ttk.Labelframe(side, text=self.l10n.t("panel.actions"), padding=16, bootstyle="light")
        actions_card.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        actions_card.columnconfigure((0, 1), weight=1)

        self.start_button = ttk.Button(
            actions_card,
            text=self.l10n.t("button.start"),
            command=self.start_typing,
            bootstyle="success",
        )
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))

        self.stop_button = ttk.Button(
            actions_card,
            text=self.l10n.t("button.stop"),
            command=self.request_stop,
            bootstyle="danger",
            state="disabled",
        )
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=(0, 8))

        ttk.Button(actions_card, text=self.l10n.t("button.load"), command=self.load_text_file, bootstyle="info").grid(
            row=1, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(actions_card, text=self.l10n.t("button.clear"), command=self.clear_text, bootstyle="secondary").grid(
            row=1, column=1, sticky="ew", padx=(6, 0)
        )

        notes_card = ttk.Labelframe(side, text=self.l10n.t("panel.notes"), padding=16, bootstyle="light")
        notes_card.grid(row=2, column=0, sticky="nsew", pady=(12, 0))

        notes = [
            self.l10n.t("note.1"),
            self.l10n.t("note.2"),
            self.l10n.t("note.3"),
            self.l10n.t("note.4"),
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
        self.hotkey_var.set(
            self.l10n.t("hotkey.ready") if result.ok else self.l10n.t("hotkey.unavailable", details=result.message)
        )

    def _on_text_modified(self, _event=None) -> None:
        self.text_box.edit_modified(False)
        self.meta_var.set(self.l10n.t("meta.actions_queued", count=count_effective_keys(self.current_text())))

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
        self._ui_queue.put(("mode", "stopped"))
        self._ui_queue.put(("status", self.l10n.t("status.stop_requested")))

    def clear_text(self) -> None:
        self.text_box.delete("1.0", END)
        self.meta_var.set(self.l10n.t("meta.actions_queued", count=0))
        self.status_var.set(self.l10n.t("status.input_cleared"))

    def load_text_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title=self.l10n.t("dialog.file_title"),
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
            messagebox.showerror(self.l10n.t("dialog.read_error_title"), str(exc))
            return

        self.text_box.delete("1.0", END)
        self.text_box.insert("1.0", text)
        self.meta_var.set(self.l10n.t("meta.actions_queued", count=count_effective_keys(self.current_text())))
        self.status_var.set(self.l10n.t("status.loaded_file", name=Path(file_path).name))

    def start_typing(self) -> None:
        if self.is_running():
            messagebox.showinfo(self.l10n.t("dialog.run_in_progress_title"), self.l10n.t("dialog.run_in_progress_body"))
            return

        text = self.current_text()
        if not text:
            messagebox.showwarning(self.l10n.t("dialog.no_text_title"), self.l10n.t("dialog.no_text_body"))
            return

        try:
            countdown = float(self.countdown_var.get())
            interval = float(self.interval_var.get())
            newline_pause = float(self.newline_pause_var.get())
        except ValueError:
            messagebox.showerror(self.l10n.t("dialog.invalid_timing_title"), self.l10n.t("dialog.invalid_timing_body"))
            return

        if countdown < 0 or interval < 0 or newline_pause < 0:
            messagebox.showerror(
                self.l10n.t("dialog.invalid_timing_title"), self.l10n.t("dialog.invalid_timing_nonnegative")
            )
            return

        actions = build_key_actions(text)
        self._stop_event.clear()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self._set_mode("countdown")
        self.status_var.set(self.l10n.t("status.preparing", count=len(actions)))
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

            self._ui_queue.put(("mode", "typing"))
            self._ui_queue.put(("status", self.l10n.t("status.typing_now")))
            type_actions(
                actions,
                emitter,
                interval=interval,
                newline_pause=newline_pause,
                stop_requested=self._stop_event.is_set,
                on_progress=on_progress,
            )
        except TypingCancelledError:
            self._ui_queue.put(("mode", "stopped"))
            self._ui_queue.put(("status", self.l10n.t("status.run_stopped")))
        except ImportError as exc:
            self._ui_queue.put(("mode", "error"))
            self._ui_queue.put(("error", self.l10n.t("dialog.dependency_error", details=exc)))
        except Exception as exc:
            self._ui_queue.put(("mode", "error"))
            self._ui_queue.put(("error", self.l10n.t("dialog.runtime_error", details=exc)))
        else:
            self._ui_queue.put(("mode", "done"))
            self._ui_queue.put(("status", self.l10n.t("status.typing_done")))
        finally:
            self._ui_queue.put(("finish", None))

    def _countdown(self, countdown: float) -> None:
        whole_seconds = int(countdown)
        remainder = countdown - whole_seconds
        for remaining in range(whole_seconds, 0, -1):
            if self._stop_event.is_set():
                raise TypingCancelledError("Stop requested during countdown.")
            self._ui_queue.put(("mode", "countdown"))
            self._ui_queue.put(("status", self.l10n.t("status.countdown_message", remaining=remaining)))
            time.sleep(1)

        if remainder > 0:
            if self._stop_event.is_set():
                raise TypingCancelledError("Stop requested during countdown.")
            self._ui_queue.put(("status", self.l10n.t("status.starting")))
            time.sleep(remainder)

    def _set_mode(self, mode: str) -> None:
        self.mode_var.set(mode)
        style = STATUS_STYLES.get(mode, {"bootstyle": "secondary"})
        self.status_badge.configure(text=self.l10n.t(f"mode.{mode}"), bootstyle=style["bootstyle"])

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
                self.meta_var.set(self.l10n.t("status.progress", done=done, total=total))
            elif kind == "error":
                self.status_var.set(str(payload))
                messagebox.showerror(self.l10n.t("dialog.error_title"), str(payload))
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
    app.meta_var.set(app.l10n.t("meta.actions_queued", count=count_effective_keys(app.current_text())))
    root.mainloop()
    return 0
