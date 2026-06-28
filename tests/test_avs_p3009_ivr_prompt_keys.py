"""P3-009: locale-keyed IVR prompt architecture.

Architecture only -- english is the only populated locale (no translation
content is in scope for this task). These tests prove the *mechanism*:
key/locale resolution, graceful fallback for missing locales/keys, and that
adding a second locale is a pure data change with zero step-handler-logic
changes required (the actual goal of P3-009, per
docs/project/implementation-backlog.md).
"""
from app.core.ivr import IvrOption
from app.core.ivr_prompts import (
    IVR_DEFAULT_LOCALE,
    PromptKey,
    _PROMPTS,
    format_option_list,
    resolve_prompt,
)


def test_resolve_prompt_returns_default_locale_template():
    assert resolve_prompt(PromptKey.BOOKING_CANCELLED) == (
        "Your appointment has been cancelled. Thank you, goodbye!"
    )


def test_resolve_prompt_interpolates_kwargs():
    result = resolve_prompt(
        PromptKey.MANAGE_BOOKING_FOUND, service_name="Haircut", when="Monday at 9:00 AM"
    )
    assert result == (
        "We found your Haircut appointment for Monday at 9:00 AM. "
        "Press 1 to cancel it, press 2 to reschedule it, or press 3 to go back to the main menu."
    )


def test_resolve_prompt_falls_back_to_default_locale_for_unknown_locale():
    """An unconfigured locale (e.g. one nobody has translated yet) must not
    raise or return a blank prompt -- it silently degrades to English."""
    known = resolve_prompt(PromptKey.SESSION_EXPIRED, locale=IVR_DEFAULT_LOCALE)
    unknown_locale_result = resolve_prompt(PromptKey.SESSION_EXPIRED, locale="xx-not-a-real-locale")
    assert unknown_locale_result == known


def test_resolve_prompt_falls_back_to_default_locale_for_missing_key(monkeypatch):
    """A *partially* translated locale (has some keys, not others) must
    fall back per-key to English rather than failing the whole prompt."""
    partial_locale = {PromptKey.BOOKING_CANCELLED: "Translated cancellation message."}
    monkeypatch.setitem(_PROMPTS, "partial", partial_locale)

    translated = resolve_prompt(PromptKey.BOOKING_CANCELLED, locale="partial")
    assert translated == "Translated cancellation message."

    untranslated_key_result = resolve_prompt(PromptKey.SESSION_EXPIRED, locale="partial")
    english_result = resolve_prompt(PromptKey.SESSION_EXPIRED, locale=IVR_DEFAULT_LOCALE)
    assert untranslated_key_result == english_result


def test_format_option_list_uses_option_item_template():
    options = (IvrOption(key="1", label="Haircut"), IvrOption(key="2", label="Manicure"))
    assert format_option_list(options) == "press 1 for Haircut, press 2 for Manicure"


def test_format_option_list_empty_options_returns_empty_string():
    assert format_option_list(()) == ""


def test_adding_a_second_locale_changes_output_with_zero_step_handler_changes(monkeypatch):
    """The actual P3-009 acceptance bar: adding a translated locale is a
    pure data change to _PROMPTS. This test adds a fake "pl" locale
    in-memory (no ivr_service.py edits) and proves resolve_prompt() picks
    it up immediately through the exact same call shape every step handler
    already uses."""
    fake_locale = dict(_PROMPTS[IVR_DEFAULT_LOCALE])
    fake_locale[PromptKey.SESSION_EXPIRED] = "Twoja sesja wygasla."
    monkeypatch.setitem(_PROMPTS, "pl", fake_locale)

    assert resolve_prompt(PromptKey.SESSION_EXPIRED, locale="pl") == "Twoja sesja wygasla."
    # Untouched locales/keys are unaffected by adding a new one.
    assert resolve_prompt(PromptKey.SESSION_EXPIRED, locale=IVR_DEFAULT_LOCALE) == (
        "Your session has expired. Please call again to book an appointment."
    )


def test_every_prompt_key_has_a_default_locale_template():
    """Guards against a future PromptKey being added without ever being
    wired into _PROMPTS[IVR_DEFAULT_LOCALE] -- resolve_prompt() would raise
    KeyError at call time instead of failing fast here."""
    missing = [key for key in PromptKey if key not in _PROMPTS[IVR_DEFAULT_LOCALE]]
    assert missing == []
