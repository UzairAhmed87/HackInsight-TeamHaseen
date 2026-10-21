"""Optional generative layer: rephrase a deterministic Insight Agent answer for residents, with guardrails.

The LLM never sees raw data and never chooses facts. It receives only the verified answer, its evidence
values and limitations, and must cite evidence as [E1], [E2]. Output is rejected, and the deterministic answer
is used instead, if it contains any number not present in that evidence, drops a required abstention,
cites evidence that does not exist, or is too long.

Configure with environment variables (any OpenAI-compatible chat-completions endpoint):
  GEMINI_API_KEY                 uses Google's OpenAI-compatible endpoint and gemini-2.5-flash
  GROQ_API_KEY                   uses Groq and llama-3.3-70b-versatile
  LLM_API_KEY, LLM_API_BASE, LLM_MODEL   any other provider
Without a key, explain() returns {"used": False, "reason": "not_configured"} and nothing is sent anywhere.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Callable

from pipeline.insight_agent import ABSTENTION

MAX_CHARS = 1400
PROVIDERS = {
    "GEMINI_API_KEY": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.5-flash"),
    "GROQ_API_KEY": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
}
LANGUAGES = {"en": "English", "ur": "Urdu (in Urdu script)"}
NUMBER = re.compile(r"(?<![\w.])[-−]?\d[\d,]*(?:\.\d+)?")
CITATION = re.compile(r"\[E(\d+)\]")
DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

SYSTEM_PROMPT = """You explain verified air-quality findings to residents of Karachi, Pakistan.
Rules you must follow:
1. Use ONLY the facts in VERIFIED_ANSWER, EVIDENCE and LIMITATIONS. Do not add any number, date, place,
   cause, health effect or comparison that is not written there. Never estimate or round to new values.
2. Cite every factual sentence with the evidence id(s) it comes from, like [E1] or [E1][E2].
3. If STATUS is "abstained", begin with exactly: I don't know based on the available evidence.
   Then explain briefly what the evidence can and cannot say. Do not guess.
4. Keep the most important limitation. Do not give medical advice.
5. Write every number with Western digits 0-9, exactly as it appears in the evidence.
6. At most 120 words. Plain language, no headings, no markdown lists."""


def _settings() -> tuple[str, str, str] | None:
    if os.environ.get("LLM_API_KEY", "").strip():
        return (
            os.environ["LLM_API_KEY"].strip(),
            os.environ.get("LLM_API_BASE", PROVIDERS["GEMINI_API_KEY"][0]).rstrip("/"),
            os.environ.get("LLM_MODEL", PROVIDERS["GEMINI_API_KEY"][1]),
        )
    for variable, (base, model) in PROVIDERS.items():
        key = os.environ.get(variable, "").strip()
        if key:
            return key, os.environ.get("LLM_API_BASE", base).rstrip("/"), os.environ.get("LLM_MODEL", model)
    return None


def _numbers(text: str) -> list[str]:
    text = CITATION.sub(" ", text.translate(DIGITS))
    return [match.replace("−", "-").replace(",", "") for match in NUMBER.findall(text)]


def _allowed_numbers(result: dict[str, Any]) -> set[str]:
    corpus = json.dumps(
        {
            "question": result.get("question"),
            "answer": result.get("answer"),
            "evidence": [item.get("values", item) for item in result.get("evidence", [])],
            "limitations": result.get("limitations"),
            "data_as_of": result.get("data_as_of"),
        },
        ensure_ascii=False,
    )
    allowed = {"2.5"}
    for token in _numbers(corpus) + re.findall(r"\d+", corpus):
        allowed.add(token.lstrip("-"))
        try:
            value = float(token)
        except ValueError:
            continue
        for digits in range(0, 4):
            allowed.add(f"{round(abs(value), digits):.{digits}f}")
        if value.is_integer():
            allowed.add(str(int(abs(value))))
    return allowed


def validate(text: str, result: dict[str, Any]) -> list[str]:
    """Return the list of guardrail violations (empty means the text may be shown)."""
    problems = []
    if not text.strip():
        return ["empty_output"]
    if len(text) > MAX_CHARS:
        problems.append("too_long")
    allowed = _allowed_numbers(result)
    unsupported = sorted({number for number in _numbers(text) if number.lstrip("-") not in allowed})
    if unsupported:
        problems.append(f"unsupported_numbers:{','.join(unsupported[:8])}")
    evidence_count = len(result.get("evidence", []))
    cited = {int(index) for index in CITATION.findall(text.translate(DIGITS))}
    if evidence_count and not cited:
        problems.append("no_citations")
    if any(index < 1 or index > evidence_count for index in cited):
        problems.append("citation_out_of_range")
    if result.get("status") == "abstained" and ABSTENTION not in text:
        problems.append("missing_abstention")
    return problems


def _prompt(result: dict[str, Any], language: str) -> str:
    evidence = {
        f"E{index}": {"source_file": item.get("source_file"), "locator": item.get("locator"), "values": item.get("values")}
        for index, item in enumerate(result.get("evidence", []), start=1)
    }
    return json.dumps(
        {
            "LANGUAGE": LANGUAGES.get(language, "English"),
            "QUESTION": result.get("question"),
            "STATUS": result.get("status"),
            "DATA_AS_OF": result.get("data_as_of"),
            "VERIFIED_ANSWER": result.get("answer"),
            "EVIDENCE": evidence,
            "LIMITATIONS": result.get("limitations"),
        },
        ensure_ascii=False,
        default=str,
    )


def _call(settings: tuple[str, str, str], system: str, user: str, timeout: float) -> str:
    key, base, model = settings
    body = json.dumps(
        {"model": model, "temperature": 0, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base}/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read())
    return payload["choices"][0]["message"]["content"].strip()


def explain(
    result: dict[str, Any],
    *,
    language: str = "en",
    timeout: float = 20.0,
    call: Callable[[str, str], str] | None = None,
) -> dict[str, Any]:
    """Return {"used", "text", "model", "reason", "violations"}; never raises for provider problems."""
    settings = _settings()
    if call is None and settings is None:
        return {"used": False, "reason": "not_configured"}
    model = settings[2] if settings else "injected"
    try:
        text = (call or (lambda system, user: _call(settings, system, user, timeout)))(SYSTEM_PROMPT, _prompt(result, language))
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError, OSError) as exc:
        return {"used": False, "reason": f"provider_error:{type(exc).__name__}", "model": model}
    violations = validate(text, result)
    if violations:
        return {"used": False, "reason": "rejected_by_guardrail", "violations": violations, "model": model}
    return {"used": True, "text": text, "model": model, "language": language, "violations": []}
