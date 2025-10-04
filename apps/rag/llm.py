# apps/rag/llm.py
from __future__ import annotations
import logging
from typing import List, Dict

from django.conf import settings
import google.generativeai as genai

log = logging.getLogger("docuchat.llm")
# System instructions for the model
# (Keep it strict so the model doesn't hallucinate outside Context.)
SYSTEM_PROMPT = (
    "You are a strict Document-QA assistant.\n"
    "Answer ONLY using the provided Context. If the answer is not in the Context, reply exactly: I don't know.\n"
    "Be concise and clear. Do NOT invent facts.\n"
)

def _configure_gemini():
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        # Fail fast: we prefer an explicit error rather than silent misuse.
        raise RuntimeError("GEMINI_API_KEY is not set")
    genai.configure(api_key=api_key)
     # Model name is configurable; default to 2.5-flash for speed + cost balance.
    model_name = getattr(settings, "GEMINI_MODEL", "models/gemini-2.5-flash")
     # Low temperature → more deterministic answers; safer for doc QA.
    generation_config = {
        "temperature": float(getattr(settings, "GEMINI_TEMPERATURE", 0.2)),
        "max_output_tokens": int(getattr(settings, "GEMINI_MAX_TOKENS", 1024)),
    }
    return genai.GenerativeModel(model_name, generation_config=generation_config)

def _build_context(cites: List[Dict], char_limit: int = 12000) -> str:
    """
    Her parça için başlık: [DOC:filename | PAGE:x | CHUNK:id]
    Gemini'nin hangi parçadan alıntı yaptığını anlamasını kolaylaştırır.
    """
    parts, used = [], 0
    for c in cites:
        head = f"[DOC:{c.get('doc','doc')} | PAGE:{c.get('page','-')} | CHUNK:{c.get('chunk_id','-')}]"
        body = (c.get("text") or c.get("snippet") or "").strip()
        if not body:
            continue
        seg = f"{head}\n{body}\n"
        seg_len = len(seg)
        # Simple truncation to keep the overall prompt bounded.
        if used + seg_len > char_limit:
            seg = seg[: max(0, char_limit - used)]
            seg_len = len(seg)
        parts.append(seg)
        used += seg_len
        if used >= char_limit:
            break
    return "\n---\n".join(parts) if parts else "(no context)"

def gemini_answer(question: str, cites: List[Dict]) -> str:
    ctx = _build_context(cites)
    # Keep the output format explicit so frontend can render consistently.
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Context:\n{ctx}\n\n"
        f"Question:\n{question}\n\n"
        "Return format:\n"
        "1) One short final answer sentence.\n"
        "2) Then the exact supporting sentence from the Context in quotes (if any).\n"
        "If no support exists in Context, respond exactly: I don't know."
    )
    model = _configure_gemini()
    try:
        resp = model.generate_content(prompt)
        text = (getattr(resp, "text", "") or "").strip()
         # Be defensive: empty responses become “I don't know.”
        return text if text else "I don't know."
    except Exception as e:
        log.exception("Gemini error")
        return f"LLM error (Gemini): {e}"

def llm_healthcheck() -> dict:
    try:
        model = _configure_gemini()
        resp = model.generate_content("Respond with a single word: ok")
        ok = bool((getattr(resp, "text", "") or "").strip())
        return {
            "provider": "gemini",
            "model": getattr(settings, "GEMINI_MODEL", "models/gemini-2.5-flash"),
            "api_key_set": True,
            "ok": ok,
            "error": None if ok else "Empty response from model",
        }
    except Exception as e:
        return {
            "provider": "gemini",
            "model": getattr(settings, "GEMINI_MODEL", "models/gemini-2.5-flash"),
            "api_key_set": bool(getattr(settings, "GEMINI_API_KEY", "")),
            "ok": False,
            "error": str(e),
        }
