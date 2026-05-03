from __future__ import annotations

import ctypes
import locale
import os
from dataclasses import dataclass


DEFAULT_LANGUAGE = "en"
CHINESE_LANGUAGE = "zh-CN"

TRANSLATIONS = {
    "en": {
        "app.tagline": "A simulated typing tool for noVNC and remote consoles.",
        "mode.ready": "Ready",
        "mode.countdown": "Countdown",
        "mode.typing": "Typing",
        "mode.stopped": "Stopped",
        "mode.done": "Done",
        "mode.error": "Error",
        "status.initial": "Paste your text, tune the timing, and start when ready.",
        "status.stop_requested": "Stop requested. Waiting for the current keystroke to finish.",
        "status.input_cleared": "Input cleared.",
        "status.loaded_file": "Loaded {name}.",
        "status.preparing": "Preparing to send {count} actions. Focus noVNC before the countdown ends.",
        "status.typing_now": "Typing into the active window now.",
        "status.run_stopped": "Run stopped. You can adjust the text and try again.",
        "status.typing_done": "Typing completed successfully.",
        "status.countdown_message": "Starting in {remaining} second(s). Focus the target window now.",
        "status.starting": "Starting...",
        "status.progress": "{done}/{total} actions sent",
        "meta.actions_queued": "{count} actions queued",
        "meta.ascii_hint": "ASCII-heavy terminal input is the most reliable.",
        "hotkey.ready": "Global Hotkey: F2 stops the active run",
        "hotkey.unavailable": "Global F2 unavailable: {details}. Try running as administrator.",
        "panel.input": "Input",
        "panel.timing": "Timing",
        "panel.actions": "Actions",
        "panel.notes": "Run Notes",
        "label.countdown": "Countdown (seconds)",
        "label.interval": "Key interval (seconds)",
        "label.newline_pause": "Newline pause (seconds)",
        "button.start": "Start Typing",
        "button.stop": "Stop Now",
        "button.load": "Load File",
        "button.clear": "Clear",
        "note.1": "1. Paste or load the full text here.",
        "note.2": "2. Click Start Typing, then focus your noVNC session.",
        "note.3": "3. TypeRelay minimizes during countdown so the target can take focus.",
        "note.4": "4. Press global F2 any time during countdown or typing to stop the run.",
        "dialog.file_title": "Select a text file",
        "dialog.read_error_title": "Unable to read file",
        "dialog.run_in_progress_title": "Run in progress",
        "dialog.run_in_progress_body": "Wait for the current run to finish or stop it with F2.",
        "dialog.no_text_title": "No text loaded",
        "dialog.no_text_body": "Paste or load the text you want to type first.",
        "dialog.invalid_timing_title": "Invalid timing value",
        "dialog.invalid_timing_body": "Countdown and delays must be numeric values.",
        "dialog.invalid_timing_nonnegative": "Timing values must be zero or greater.",
        "dialog.error_title": "TypeRelay",
        "dialog.dependency_error": "Missing dependency: {details}. Install requirements and relaunch.",
        "dialog.runtime_error": "Typing failed: {details}",
    },
    "zh-CN": {
        "app.tagline": "一个用于 noVNC 和远程控制台的模拟输入工具。",
        "mode.ready": "就绪",
        "mode.countdown": "倒计时",
        "mode.typing": "输入中",
        "mode.stopped": "已停止",
        "mode.done": "已完成",
        "mode.error": "错误",
        "status.initial": "粘贴文本，调整参数，然后开始输入。",
        "status.stop_requested": "已请求停止，正在等待当前按键结束。",
        "status.input_cleared": "内容已清空。",
        "status.loaded_file": "已加载 {name}。",
        "status.preparing": "准备发送 {count} 个动作。请在倒计时结束前切换到 noVNC。",
        "status.typing_now": "正在向当前活动窗口模拟输入。",
        "status.run_stopped": "本次任务已停止。你可以调整文本后再次开始。",
        "status.typing_done": "输入已完成。",
        "status.countdown_message": "将在 {remaining} 秒后开始。请现在切换到目标窗口。",
        "status.starting": "即将开始...",
        "status.progress": "已发送 {done}/{total} 个动作",
        "meta.actions_queued": "{count} 个待发送动作",
        "meta.ascii_hint": "以 ASCII 为主的终端输入通常最稳定。",
        "hotkey.ready": "全局热键：F2 可停止当前任务",
        "hotkey.unavailable": "全局 F2 不可用：{details}。可尝试以管理员身份运行。",
        "panel.input": "输入内容",
        "panel.timing": "时间设置",
        "panel.actions": "操作",
        "panel.notes": "使用说明",
        "label.countdown": "启动倒计时（秒）",
        "label.interval": "按键间隔（秒）",
        "label.newline_pause": "换行停顿（秒）",
        "button.start": "开始输入",
        "button.stop": "立即停止",
        "button.load": "导入文件",
        "button.clear": "清空",
        "note.1": "1. 在这里粘贴完整文本，或导入一个文本文件。",
        "note.2": "2. 点击“开始输入”，然后切换到 noVNC 会话。",
        "note.3": "3. 倒计时期间 TypeRelay 会自动最小化，方便目标窗口获得焦点。",
        "note.4": "4. 倒计时或输入过程中，随时按全局 F2 停止本次任务。",
        "dialog.file_title": "选择文本文件",
        "dialog.read_error_title": "读取文件失败",
        "dialog.run_in_progress_title": "任务进行中",
        "dialog.run_in_progress_body": "请等待当前任务结束，或按 F2 停止。",
        "dialog.no_text_title": "没有可输入的文本",
        "dialog.no_text_body": "请先粘贴或导入要发送的文本。",
        "dialog.invalid_timing_title": "时间参数无效",
        "dialog.invalid_timing_body": "倒计时和延迟必须是数字。",
        "dialog.invalid_timing_nonnegative": "所有时间参数都必须大于或等于 0。",
        "dialog.error_title": "TypeRelay",
        "dialog.dependency_error": "缺少依赖：{details}。请安装 requirements 后重新运行。",
        "dialog.runtime_error": "输入失败：{details}",
    },
}


def _windows_ui_locale() -> str | None:
    if not hasattr(ctypes, "windll"):
        return None
    try:
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        return locale.windows_locale.get(lang_id)
    except Exception:
        return None


def _default_locale_name() -> str | None:
    windows_locale = _windows_ui_locale()
    if windows_locale:
        return windows_locale

    try:
        current_locale = locale.getlocale()[0]
    except Exception:
        current_locale = None

    if current_locale:
        return current_locale

    for key in ("LC_ALL", "LANG", "LANGUAGE"):
        value = os.environ.get(key)
        if value:
            return value
    return None


def detect_language(locale_name: str | None = None) -> str:
    probe = (locale_name or _default_locale_name() or "").lower()
    if probe.startswith("zh"):
        return CHINESE_LANGUAGE
    return DEFAULT_LANGUAGE


@dataclass(frozen=True)
class Localizer:
    language: str

    def t(self, key: str, **values: object) -> str:
        language = self.language if self.language in TRANSLATIONS else DEFAULT_LANGUAGE
        template = TRANSLATIONS[language].get(key) or TRANSLATIONS[DEFAULT_LANGUAGE].get(key) or key
        return template.format(**values)


def build_localizer(locale_name: str | None = None) -> Localizer:
    return Localizer(detect_language(locale_name))
