import html

from app.core.ivr import IvrAction, IvrResponse


def ivr_to_twiml(
    response: IvrResponse,
    *,
    gather_action_url: str | None = None,
    transfer_to: str | None = None,
) -> str:
    """Convert an IvrResponse to a TwiML XML string.

    - CONTINUE: <Gather> wrapping <Say> so next digit POSTs back
    - END: <Say> then <Hangup>
    - TRANSFER: <Say> then <Dial>; falls back to <Hangup> when no number
    """
    prompt = html.escape(response.prompt)

    if response.action == IvrAction.CONTINUE and gather_action_url:
        url = html.escape(gather_action_url)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<Response>\n"
            f'  <Gather numDigits="1" action="{url}" method="POST">\n'
            f"    <Say>{prompt}</Say>\n"
            "  </Gather>\n"
            "  <Say>We didn't receive your input. Goodbye.</Say>\n"
            "  <Hangup/>\n"
            "</Response>"
        )

    if response.action == IvrAction.TRANSFER and transfer_to:
        number = html.escape(transfer_to)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<Response>\n"
            f"  <Say>{prompt}</Say>\n"
            f"  <Dial>{number}</Dial>\n"
            "</Response>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        f"  <Say>{prompt}</Say>\n"
        "  <Hangup/>\n"
        "</Response>"
    )
