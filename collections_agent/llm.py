"""One small model-agnostic LLM call (LiteLLM) with a disk cache and rate-limit back-off."""
import hashlib
import json
import os
import time
from pathlib import Path

import litellm
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"
load_dotenv(ROOT / ".env")
litellm.suppress_debug_info = True

MODEL = os.getenv("AGENT_MODEL", "groq/openai/gpt-oss-120b")


def chat(messages, model=MODEL, temperature=0.0, json_mode=False):
    key = hashlib.sha256(json.dumps([model, temperature, json_mode, messages]).encode()).hexdigest()
    path = CACHE / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["text"]
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    if "gpt-oss" in model:  # reasoning model: keep thinking short so the spoken reply fits the token budget
        kwargs["reasoning_effort"] = "low"
    for attempt in range(8):
        try:
            resp = litellm.completion(model=model, messages=messages, temperature=temperature, max_tokens=1200, **kwargs)
            break
        except litellm.RateLimitError:
            time.sleep(min(60, 8 * (attempt + 1)))
    else:
        raise RuntimeError("rate limited too many times")
    text = (resp.choices[0].message.content or "").strip()
    CACHE.mkdir(exist_ok=True)
    path.write_text(json.dumps({"model": model, "text": text}), encoding="utf-8")
    return text
