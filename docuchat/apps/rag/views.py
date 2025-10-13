# apps/rag/views.py
from __future__ import annotations
import re, logging
from typing import List, Dict, Optional

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings

from apps.uploads.models import Chunk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .llm import gemini_answer, llm_healthcheck

log = logging.getLogger("docuchat.ask")


def retrieve(question: str, top_k: int = 3) -> List[Dict]:
    """
    TF-IDF tabanlı basit retriever.
    Dönüş: doc, doc_id, page, chunk_id, text, snippet
    """
    
    # her zaman nullable olmayabilirmiş try --> alanları only ile çekmek farklı.
    chunks = list(
        # Keep the select list minimal to reduce DB I/O.
        Chunk.objects.select_related("document")
        .only("id", "text", "document_id")  # performans için minimal kolon seti
        .all()
    )
    if not chunks:
        return []

    corpus = [(c.text or "") for c in chunks]

    # Türkçe/çok dilli korpuslar için stop_words=None (İngilizce stop sözlüğü
    # Türkçe performansı düşürmesin)
    # Use no built-in stopwords: English stoplists hurt Turkish/multilingual recall.
    vectorizer = TfidfVectorizer(stop_words=None)
    tfidf = vectorizer.fit_transform(corpus + [question])
    sims = cosine_similarity(tfidf[-1], tfidf[:-1]).flatten()
    idxs = sims.argsort()[::-1][:top_k]

    results: List[Dict] = []
    for i in idxs:
        c = chunks[i]
        text = (c.text or "").strip()
 # Prefer filename; fall back to a synthetic name.
        doc_obj = getattr(c, "document", None)
        # doc adı için fallback: önce filename, sonra "doc-{id}"
        if doc_obj is not None:
            doc_name = getattr(doc_obj, "filename", None) or f"doc-{getattr(c, 'document_id', 'unknown')}"
            doc_id = getattr(doc_obj, "id", getattr(c, "document_id", None))
        else:
            doc_name = f"doc-{getattr(c, 'document_id', 'unknown')}"
            doc_id = getattr(c, "document_id", None)

        results.append({
            "doc": doc_name,
            "doc_id": doc_id,
            "page": getattr(c, "page", None),     # modelde mevcut; null olabilir
            "chunk_id": c.id,
            "text": text,
            "snippet": (text[:280] + "…") if len(text) > 280 else text,
        })
    return results

# Lightweight, language-agnostic heuristics to pick a single strong quote.

_SENT_SPLIT = re.compile(r'(?<=[\.\!\?])\s+|\n+')

def _split_sentences(text: str) -> List[str]:
    parts = [s.strip() for s in _SENT_SPLIT.split(text or "") if s.strip()]
    return parts or ([] if not text else [text.strip()])

def _score_sentence(q: str, s: str) -> float:
    ql, sl = q.lower(), s.lower()
    score = 0.0
    # key word match
    keys = re.findall(r'\w+', ql)
    for k in set(keys):
        # Keyword containment (>=4 chars to avoid noise).
        if len(k) >= 4 and k in sl:
            score += 1.0
    # date/nums clues
    if re.search(r'\b\d{1,2}\.\d{1,2}\.\d{4}\b', s):  # 01.10.2025
        score += 2.0
    if re.search(r'\b20\d{2}\b', s):
        score += 0.5
    # shorten the longer sent.
    score -= min(len(s) / 500.0, 0.5)
    return score

def _domain_hint_patterns() -> List[re.Pattern]:
    # Domain-specific shortcuts: pull exact “start of semester” lines first.
    
    hints = [
        r"Semesterbeginn.*?\d{1,2}\.\d{1,2}\.\d{4}",
        r"Start of semester.*?\d{1,2}\.\d{1,2}\.\d{4}",
        r"Semester start.*?\d{1,2}\.\d{1,2}\.\d{4}",
    ]
    return [re.compile(h, re.I) for h in hints]

def best_sentence_for_chunk(question: str, chunk_text: str) -> Optional[str]:
    sents = _split_sentences(chunk_text)
    if not sents:
        return None
    # 1) domain clues
    for pat in _domain_hint_patterns():
        for s in sents:
            if pat.search(s):
                return s.strip()
    # 2) general score
    best_s, best_sc = None, float("-inf")
    for s in sents:
        sc = _score_sentence(question, s)
        if sc > best_sc:
            best_s, best_sc = s, sc
    return best_s.strip() if best_s else None


def fake_llm_answer(question: str, cites: List[Dict]) -> str:
    if cites:
        lead = cites[0]
        p = f"(p.{lead['page']})" if lead.get("page") else ""
        return f"According to {lead['doc']} {p}: {lead['snippet']}"
    return "I don't know."


@api_view(['POST'])
def ask(request):
    q = (request.data.get('question') or "").strip()
    if not q:
        return Response({"answer": "Please provide a question.", "citations": []})

    top_k = int(getattr(settings, 'TOP_K', 4))
    raw_cites = retrieve(q, top_k=top_k)

    # her cite için tek güçlü destek cümlesi
    enriched = []
    for c in raw_cites:
        quote = best_sentence_for_chunk(q, c["text"])
        enriched.append({
            "doc": c["doc"],
            "doc_id": c["doc_id"],
            "page": c["page"],
            "chunk_id": c["chunk_id"],
            "snippet": c["snippet"],
            "quote": quote or c["snippet"],
        })

    # LLM choice - Gemini is wanted but in case of any sit. fake one is defined
    llm_provider = getattr(settings, 'LLM_PROVIDER', 'gemini')
    use_gemini = (llm_provider == 'gemini' and bool(getattr(settings, 'GEMINI_API_KEY', '')))

    if use_gemini:
        log.info("🧠 Using Gemini backend for ask()")
        ans = gemini_answer(q, raw_cites)
    else:
        log.info("⚙️ Using Fake LLM backend for ask()")
        ans = fake_llm_answer(q, raw_cites)

    return Response({
        "answer": ans or "I don't know.",
        "citations": enriched,
    })


@api_view(['GET'])
def llm_health(request):
    return Response(llm_healthcheck())
