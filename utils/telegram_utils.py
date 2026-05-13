import hashlib
import hmac
from urllib.parse import parse_qsl


def validate_init_data(init_data: str, bot_token: str) -> dict:
    data = dict(parse_qsl(init_data))
    received_hash = data.pop("hash", "")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("init_data validation failed")
    return data
