from __future__ import annotations
import logging
from typing import List, Dict
from django.conf import settings
import google.generativeai as genai

log = logging.getLogger("docuchat.llm")

SYSTEM_PROMPT = (
    "You are a strict Document-QA assistant.\n"
    "Only answer using the provided Context. If the answer is not in the Context, reply exactly: I don't know.\n"
    "Prefer verbatim facts (versions, dates, numbers). Be concise. Do not invent anything.\n"
)

def _configure_gemini():
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    genai.configure(api_key=api_key)
    model_name = getattr(settings, "GEMINI_MODEL", "models/gemini-2.5-flash")
    generation_config = {
        # daha deterministik
        "temperature": float(getattr(settings, "GEMINI_TEMPERATURE", 0.1)),
        "max_output_tokens": int(getattr(settings, "GEMINI_MAX_TOKENS", 1536)),
    }
    return genai.GenerativeModel(model_name, generation_config=generation_config)

def _build_context(cites: List[Dict], char_limit: int = 16000) -> str:
    """
    cites beklenen alanlar: doc, page, chunk_id, text/snippet, quote
    quote -> önce; ardından kısa snippet (varsa)
    """
    parts, used = [], 0
    for c in cites:
        head = f"[DOC:{c.get('doc','doc')} | PAGE:{c.get('page','-')} | CHUNK:{c.get('chunk_id','-')}]"
        quote = (c.get("quote") or "").strip()
        snippet = (c.get("snippet") or c.get("text") or "").strip()
        body_lines = []
        if quote:
            body_lines.append(f"QUOTE: \"{quote}\"")
        if snippet and snippet != quote:
            body_lines.append(f"SNIPPET: {snippet}")
        if not body_lines:
            continue
        seg = f"{head}\n" + "\n".join(body_lines) + "\n"
        seg_len = len(seg)
        if used + seg_len > char_limit:
            seg = seg[: max(0, char_limit - used)]
            seg_len = len(seg)
        parts.append(seg); used += seg_len
        if used >= char_limit:
            break
    return "\n---\n".join(parts) if parts else "(no context)"

def gemini_answer(question: str, cites: List[Dict]) -> str:
    ctx = _build_context(cites)
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Context:\n{ctx}\n\n"
        f"Question:\n{question}\n\n"
        "Return format:\n"
        "1) One short final answer.\n"
        "2) Then the exact supporting sentence from Context in quotes (if any).\n"
        "If no support exists in Context, respond exactly: I don't know."
    )
    model = _configure_gemini()
    try:
        resp = model.generate_content(prompt)
        text = (getattr(resp, "text", "") or "").strip()
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

def fake_llm_answer(question: str, cites: List[Dict]) -> str:
    if cites:
        lead = cites[0]
        p = f"(p.{lead.get('page')})" if lead.get("page") else ""
        q = lead.get("quote") or lead.get("snippet") or ""
        return f"According to {lead['doc']} {p}: {q}"
    return "I don't know."
