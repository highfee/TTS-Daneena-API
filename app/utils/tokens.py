import secrets
import string

def generate_auth_token() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)
