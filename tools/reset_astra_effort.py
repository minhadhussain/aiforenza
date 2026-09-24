"""Reset only a remembered AI Forenza Astra Low choice to its configured default.

Close OpenCode first: a running client can write its cached selection back.
Other model preferences and explicitly selected non-Low efforts are preserved.
"""

import json
import os
from pathlib import Path
import tempfile

MODEL = "aiforenza/gpt-6-astra"


def reset_saved_low(path: Path) -> bool:
    if not path.exists():
        return False
    original = path.read_bytes()
    data = json.loads(original)
    if not isinstance(data, dict) or not isinstance(data.get("variant"), dict):
        return False
    if data["variant"].get(MODEL) != "low":
        return False
    data["variant"][MODEL] = "default"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix="astra-effort-", suffix=".tmp", delete=False) as file:
            temporary = Path(file.name)
            file.write((json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
        if path.read_bytes() != original:
            raise RuntimeError("Selection state changed. Close OpenCode and retry.")
        temporary.replace(path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
    return True


def main():
    root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    changed = reset_saved_low(root / "opencode/model.json")
    print(json.dumps({"model": MODEL, "saved_low_reset": changed, "configured_default": "medium", "other_model_choices_preserved": True}))
    print("Reopen OpenCode to load the selection. Explicit effort choices remain supported.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc) if type(exc) is RuntimeError else "Selection reset failed: " + type(exc).__name__)
        raise SystemExit(1)
