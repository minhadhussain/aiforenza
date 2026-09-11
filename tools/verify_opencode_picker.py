"""Windows TUI picker check using pywinpty; never submits an inference prompt."""

import argparse
import json
import os
import re
import select
import time
from pathlib import Path

from winpty import PtyProcess
from configure_opencode_global import ROOT, executable


def plain(text):
    text = re.sub(r"\x1b\][^\x07]*(?:\x07|\x1b\\)", "", text)
    return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)


def read_for(proc, seconds):
    chunks = []
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if select.select([proc.fileobj], [], [], 0.15)[0]:
            try:
                chunks.append(proc.read(65536))
            except EOFError:
                break
    return plain("".join(chunks))


def main(directory):
    env = os.environ.copy()
    env.update(OPENCODE_DISABLE_AUTOUPDATE="true", TERM="xterm-256color")
    proc = PtyProcess.spawn(
        [str(executable())], cwd=str(directory), env=env, dimensions=(50, 160)
    )
    try:
        startup = read_for(proc, 20)
        print(
            json.dumps(
                {"startup_alive": proc.isalive(), "rendered_chars": len(startup)}
            ),
            flush=True,
        )
        # Default leader Ctrl+X then m opens the model dialog without any Enter key.
        proc.write("\x18")
        time.sleep(0.2)
        proc.write("m")
        picker = read_for(proc, 8)
        opened = any(
            s in picker.lower()
            for s in ("select model", "models", "favorites", "recent")
        )
        print(
            json.dumps(
                {
                    "picker_opened": opened,
                    "astra_visible_before_search": "GPT-6 Astra" in picker,
                    "forenza_visible_before_search": "Forenza" in picker,
                }
            ),
            flush=True,
        )
        if not opened:
            raise RuntimeError(
                "Could not confirm model dialog; no further keyboard input sent"
            )
        proc.write("astra")
        result = read_for(proc, 5)
        visible = "GPT-6 Astra" in result
        print(
            json.dumps(
                {
                    "directory": str(directory),
                    "astra_visible_in_picker_search": visible,
                    "ai_forenza_label_visible": "Forenza" in result,
                    "no_inference_submitted": True,
                }
            ),
            flush=True,
        )
        if not visible:
            raise RuntimeError("Astra not observed in terminal picker search")
        proc.write("\x1b")
        read_for(proc, 1)
    finally:
        # Only close the test terminal we created, never existing user sessions.
        proc.close(force=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", default=str(ROOT))
    args = parser.parse_args()
    try:
        main(Path(args.directory))
    except Exception as exc:
        print(
            str(exc)
            if type(exc) is RuntimeError
            else "Picker test failed: " + type(exc).__name__
        )
        raise SystemExit(1)
