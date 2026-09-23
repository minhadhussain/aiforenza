"""Windows TUI picker check using pywinpty; never submits an inference prompt."""

import argparse
import json
import os
import re
import select
import subprocess
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


def stop_tui(process):
    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
    try:
        process.close(force=True)
    except OSError:
        pass  # ConPTY may report access denied for the already terminated handle.


def main(directory, verify_variants=False, environment=None, model_slug="gpt-6-astra", efforts=None):
    labels = {"gpt-5.4": ("GPT-5.4", "gpt-5.4"), "gpt-5.6-sol": ("GPT-5.6 Sol", "sol"), "gpt-6-astra": ("GPT-6 Astra", "astra")}
    label, search = labels[model_slug]
    expected = set(efforts or ["low", "medium", "high", "xhigh"] + ([] if model_slug == "gpt-5.4" else ["max"]) + ([] if model_slug == "gpt-6-astra" else ["none"]))
    env = (environment if environment is not None else os.environ).copy()
    env.update(OPENCODE_DISABLE_AUTOUPDATE="true", TERM="xterm-256color")
    if verify_variants:
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps({"enabled_providers": ["aiforenza"]})
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
                    "model_visible_before_search": label in picker,
                    "forenza_visible_before_search": "Forenza" in picker,
                }
            ),
            flush=True,
        )
        if not opened:
            raise RuntimeError(
                "Could not confirm model dialog; no further keyboard input sent"
            )
        proc.write(search)
        proc.setwinsize(51, 161)
        result = read_for(proc, 5)
        visible = label in result
        print(
            json.dumps(
                {
                    "directory": str(directory),
                    "model": model_slug,
                    "model_visible_in_picker_search": visible,
                    "ai_forenza_label_visible": "Forenza" in result,
                    "no_inference_submitted": True,
                }
            ),
            flush=True,
        )
        if not visible:
            raise RuntimeError("Requested model not observed in terminal picker search")
        if verify_variants:
            proc.write("\r")  # Select the AI Forenza model, without a prompt.
            read_for(proc, 3)
            observed = set()
            for step in range(len(expected) + 2):
                proc.write("\x14")  # Default Ctrl+T: cycle model reasoning variant.
                proc.setwinsize(50 + step % 2, 160 + step % 2)
                footer = read_for(proc, 2)
                observed.update(re.findall(r"\b(none|low|medium|high|xhigh|max)\b", footer.lower()))
            print(json.dumps({"selected_model": "aiforenza/" + model_slug, "observed_effort_labels": sorted(observed), "no_inference_submitted": True}), flush=True)
            if observed != expected:
                raise RuntimeError("Not every reasoning variant appeared in the TUI")
        else:
            proc.write("\x1b")
            read_for(proc, 1)
    finally:
        # Only close the test terminal we created, never existing user sessions.
        stop_tui(proc)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", default=str(ROOT))
    parser.add_argument("--variants", action="store_true")
    parser.add_argument("--model", choices=["gpt-5.4", "gpt-5.6-sol", "gpt-6-astra"], default="gpt-6-astra")
    parser.add_argument("--efforts", nargs="+")
    args = parser.parse_args()
    try:
        main(Path(args.directory), args.variants, model_slug=args.model, efforts=args.efforts)
    except Exception as exc:
        print(
            str(exc)
            if type(exc) is RuntimeError
            else "Picker test failed: " + type(exc).__name__
        )
        raise SystemExit(1)
