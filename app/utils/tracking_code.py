"""Un-guessable tracking code generation.

Format: FRK-XXXXXXXXXXXX (12 uppercase hex chars = 48 bits of randomness from
the `secrets` module). It deliberately contains NO personal data such as the
national code.
"""
import secrets

TRACKING_CODE_PREFIX = "FRK"


def generate_tracking_code() -> str:
    return f"{TRACKING_CODE_PREFIX}-{secrets.token_hex(6).upper()}"
