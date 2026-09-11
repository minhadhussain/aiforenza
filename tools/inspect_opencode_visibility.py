"""Read effective OpenCode configs without printing secrets, prompts, or raw logs."""

import json
import os
import re
import subprocess
from pathlib import Path

from configure_opencode_global import executable, ROOT


def summary(config):
    provider = config.get("provider", {}).get("aiforenza", {})
    return {
        "provider_present": bool(provider),
        "model_ids": list(provider.get("models", {})),
        "astra_blacklisted": "gpt-6-astra" in provider.get("blacklist", []),
        "astra_whitelisted": "gpt-6-astra" in provider["whitelist"]
        if "whitelist" in provider
        else None,
        "provider_disabled": "aiforenza" in config.get("disabled_providers", []),
        "provider_allowlisted": "aiforenza" in config["enabled_providers"]
        if "enabled_providers" in config
        else None,
        "astra_name": provider.get("models", {}).get("gpt-6-astra", {}).get("name"),
        "default_is_astra": config.get("model") == "aiforenza/gpt-6-astra",
    }


def main():
    print(
        json.dumps(
            {
                "override_variables_present": [
                    k
                    for k in (
                        "OPENCODE_CONFIG",
                        "OPENCODE_CONFIG_CONTENT",
                        "OPENCODE_CONFIG_DIR",
                        "XDG_CONFIG_HOME",
                    )
                    if os.environ.get(k)
                ]
            }
        )
    )
    for directory in (
        ROOT,
        Path.home() / "OneDrive/Desktop",
        Path.home() / "bug-bounty",
    ):
        if not directory.is_dir():
            continue
        result = subprocess.run(
            [str(executable()), "debug", "config"],
            cwd=directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
        if result.returncode != 0:
            print(json.dumps({"directory": str(directory), "config_error": True}))
            continue
        try:
            config = json.loads(result.stdout)
        except ValueError:
            print(json.dumps({"directory": str(directory), "unparsed_output": True}))
            continue
        print(json.dumps({"directory": str(directory), **summary(config)}))
    # Process command lines are inspected in memory; only safe switches/paths are reported.
    ps = 'Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "opencode.exe" } | Select-Object ProcessId,ParentProcessId,CommandLine,CreationDate | ConvertTo-Json'
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
        timeout=30,
    )
    rows = json.loads(result.stdout) if result.stdout.strip() else []
    if isinstance(rows, dict):
        rows = [rows]
    for row in rows:
        command = row.get("CommandLine") or ""
        print(
            json.dumps(
                {
                    "pid": row["ProcessId"],
                    "parent_pid": row["ParentProcessId"],
                    "created": row.get("CreationDate"),
                    "mode_flags": [
                        word
                        for word in ("attach", "serve", "web", "--model", "--port")
                        if re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", command)
                    ],
                    "known_workspaces": [
                        name
                        for name in ("aiforenza", "bug-bounty", "Desktop")
                        if name.lower() in command.lower()
                    ],
                }
            )
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Visibility inspection stopped:", type(exc).__name__)
        raise SystemExit(1)
