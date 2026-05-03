from typerelay.i18n import DEFAULT_LANGUAGE, Localizer, detect_language


def test_detect_language_prefers_chinese_for_zh_locales() -> None:
    assert detect_language("zh_CN") == "zh-CN"
    assert detect_language("zh-Hans-CN") == "zh-CN"


def test_detect_language_falls_back_to_english_for_other_locales() -> None:
    assert detect_language("en_US") == "en"
    assert detect_language("ja_JP") == "en"
    assert detect_language("unknown") == DEFAULT_LANGUAGE


def test_localizer_returns_translated_strings_and_formats_values() -> None:
    zh = Localizer("zh-CN")
    en = Localizer("en")

    assert zh.t("app.tagline") == "一个用于 noVNC 和远程控制台的模拟输入工具。"
    assert en.t("mode.ready") == "Ready"
    assert zh.t("meta.actions_queued", count=12) == "12 个待发送动作"
