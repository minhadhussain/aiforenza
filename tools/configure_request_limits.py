"""Update only the local HTTP body cap; never print/read other env values to output."""

from pathlib import Path
from dotenv import dotenv_values, set_key

root = Path(__file__).resolve().parents[1]
path = root / ".env"
if not path.is_file():
    raise SystemExit("Root .env missing; configure required credentials first")
current = dotenv_values(path).get("API_MAX_REQUEST_BYTES")
if current not in (None, "", "200000", "1000000"):
    raise SystemExit(
        "Custom API_MAX_REQUEST_BYTES already set; review before replacing"
    )
set_key(str(path), "API_MAX_REQUEST_BYTES", "1000000", quote_mode="never")
print("API_MAX_REQUEST_BYTES=1000000; all other environment values preserved")
