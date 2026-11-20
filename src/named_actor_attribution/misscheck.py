"""The miss check (spec §7, step 2): a second model lists what the annotation may have missed,
and the segments it doubts. Its flags go into the document for the reviewer; nothing is
filtered out, so that problems with the prompt stay visible.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import markup

ROOT = Path(__file__).resolve().parents[2]
PROMPT = ROOT / "prompts" / "miss-check.md"
GUIDELINES = ROOT / "guidelines.md"
DEFAULT_MODEL = "deepseek/deepseek-v4-pro-0813"
URL = "https://openrouter.ai/api/v1/chat/completions"
KEY_NAMES = ("NAA_API_KEY",)


class MissCheckError(RuntimeError):
    pass


def api_key(env_file: Path = ROOT / ".env") -> str:
    """The OpenRouter key, from the environment or the repo's .env file."""
    for name in KEY_NAMES:
        if os.environ.get(name):
            return os.environ[name]
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, _, value = line.partition("=")
            if name.strip() in KEY_NAMES and value.strip():
                return value.strip().strip('"').strip("'")
    raise MissCheckError(f"no OpenRouter key: set {' or '.join(KEY_NAMES)}, in the environment or in .env")


def instructions() -> str:
    return PROMPT.read_text(encoding="utf-8") + GUIDELINES.read_text(encoding="utf-8")


def document_for_model(doc: markup.Document) -> str:
    """The document as the model sees it: the markup, without flags or review details."""
    shown = markup.Document(**{**doc.__dict__, "flags": [], "notes": None, "annotator": None})
    return markup.serialize(shown)


def ask(model: str, system: str, user: str, key: str, timeout: int = 180, tries: int = 3) -> dict:
    # Reasoning is off: with it, DeepSeek V4.1 Flash reasoned until it ran out of tokens and never
    # answered, whatever the effort or budget asked (tried on the pilot, 2026-11-20). Without it,
    # V4 Pro made fewer mistakes than V4.1 Flash on the pilot, so it is the default.
    body = json.dumps({
        "model": model, "temperature": 0, "response_format": {"type": "json_object"},
        "reasoning": {"enabled": False}, "max_tokens": 4000,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }).encode("utf-8")
    request = urllib.request.Request(URL, data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
        "User-Agent": "named-actor-attribution", "X-Title": "named-actor-attribution"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == tries - 1:
                raise MissCheckError(f"OpenRouter: {e}") from None
            time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def parse_flags(content: str) -> list[markup.Flag]:
    # Some answers wrap the JSON in a Markdown code fence despite the JSON response format.
    fenced = re.fullmatch(r"\s*```(?:json)?\s*(.*?)\s*```\s*", content, re.S)
    if fenced:
        content = fenced.group(1)
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise MissCheckError(f"the answer is not JSON: {e}: {content[:200]!r}") from None
    flags = data.get("flags") if isinstance(data, dict) else None
    if not isinstance(flags, list):
        raise MissCheckError(f"the answer has no list of flags: {content[:200]!r}")
    out = []
    for f in flags:
        if not isinstance(f, dict):
            continue
        out.append(markup.Flag(kind=str(f.get("kind", "")), quote=str(f.get("quote", "")),
                               reason=str(f.get("reason") or ""), speaker=f.get("speaker") or None))
    return out


def check_document(doc: markup.Document, model: str = DEFAULT_MODEL, key: str | None = None) -> tuple[list[markup.Flag], dict]:
    """Run the miss check on one document. Returns its flags, and the answer's usage and provider."""
    answer = ask(model, instructions(), document_for_model(doc), key or api_key())
    try:
        choice = answer["choices"][0]
        content = choice["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise MissCheckError(f"unexpected answer: {json.dumps(answer)[:300]}") from None
    if choice.get("finish_reason") not in (None, "stop"):
        raise MissCheckError(f"the answer was cut off ({choice.get('finish_reason')})")
    return parse_flags(content), {"usage": answer.get("usage"), "provider": answer.get("provider")}
