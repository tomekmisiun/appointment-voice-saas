import html

from app.core.ivr import IvrAction, IvrResponse
from app.core.ivr_prompts import IVR_DEFAULT_LOCALE, PromptKey, resolve_prompt

# Twilio <Say> "language" attribute (selects the TTS voice/accent), keyed by
# this app's own locale codes. Without this, Twilio defaults to an English
# voice reading the text literally -- a Polish prompt string read by an
# English voice is unintelligible, even though the words are correct.
_TWIML_LANGUAGE_BY_LOCALE = {
    "en": "en-US",
    "pl": "pl-PL",
}
_DEFAULT_TWIML_LANGUAGE = "en-US"


def _twiml_language(locale: str) -> str:
    return _TWIML_LANGUAGE_BY_LOCALE.get(locale, _DEFAULT_TWIML_LANGUAGE)


def ivr_to_twiml(
    response: IvrResponse,
    *,
    gather_action_url: str | None = None,
    transfer_to: str | None = None,
    locale: str = IVR_DEFAULT_LOCALE,
) -> str:
    """Convert an IvrResponse to a TwiML XML string.

    - CONTINUE: <Gather> wrapping <Say> so next digit POSTs back
    - END: <Say> then <Hangup>
    - TRANSFER: <Say> then <Dial>; falls back to <Hangup> when no number

    `locale` drives the TTS voice via <Say language="...">, on every <Say>
    tag including the no-input fallback (also localized, via
    PromptKey.NO_INPUT_GOODBYE, rather than a hardcoded English literal).
    """
    prompt = html.escape(response.prompt)
    language = _twiml_language(locale)

    if response.action == IvrAction.CONTINUE and gather_action_url:
        url = html.escape(gather_action_url)
        no_input_goodbye = html.escape(resolve_prompt(PromptKey.NO_INPUT_GOODBYE, locale=locale))
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<Response>\n"
            f'  <Gather numDigits="1" action="{url}" method="POST">\n'
            f'    <Say language="{language}">{prompt}</Say>\n'
            "  </Gather>\n"
            f'  <Say language="{language}">{no_input_goodbye}</Say>\n'
            "  <Hangup/>\n"
            "</Response>"
        )

    if response.action == IvrAction.TRANSFER and transfer_to:
        number = html.escape(transfer_to)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<Response>\n"
            f'  <Say language="{language}">{prompt}</Say>\n'
            f"  <Dial>{number}</Dial>\n"
            "</Response>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        f'  <Say language="{language}">{prompt}</Say>\n'
        "  <Hangup/>\n"
        "</Response>"
    )
