"""Admission estimates are NOT billing usage or a reduction of reservation capacity."""

import json
import math
from functools import lru_cache

import tiktoken

SUPPORTED_ESTIMATES = {"gpt-5.4", "gpt-5.6-sol", "gpt-6-astra", "grok-4.6"}


@lru_cache(maxsize=1)
def encodings():
    return (tiktoken.get_encoding("o200k_base"), tiktoken.get_encoding("cl100k_base"))


def input_budgets(request):
    payload = request.model_dump(exclude_none=True)
    serialized = json.dumps(payload, ensure_ascii=False)
    overhead = 64 * len(request.messages) + 256
    byte_bound = len(serialized.encode("utf-8")) + overhead
    if request.model not in SUPPORTED_ESTIMATES:
        return byte_bound, byte_bound, "utf8_upper_bound"
    # Include messages, tool calls/results, schemas, and extra fields. Count both
    # encodings, then add 25% and framing overhead. These are explicit surrogates
    # for deployments whose exact tokenizer is not published; never bill from them.
    try:
        count = max(
            len(enc.encode(serialized, disallowed_special=())) for enc in encodings()
        )
    except Exception:
        return byte_bound, byte_bound, "utf8_fallback"
    estimate = math.ceil(count * 1.25) + overhead
    return estimate, max(byte_bound, estimate), "dual_encoding_margin"
