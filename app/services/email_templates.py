from urllib.parse import urlencode


def build_password_reset_url(base_url: str, token: str) -> str:
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode({'token': token})}"


def render_password_reset_subject() -> str:
    return "Reset your password"


def render_password_reset_body(reset_url: str) -> str:
    return (
        "A password reset was requested for your account.\n\n"
        f"Reset your password here: {reset_url}\n\n"
        "If you did not request this change, you can ignore this email."
    )
