from __future__ import annotations
import logging, re
from typing import List, Dict, Optional
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from apps.uploads.models import Chunk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rank_bm25 import BM25Okapi
from django.core.cache import cache
from .llm import gemini_answer, llm_healthcheck, fake_llm_answer
from rest_framework import status
log = logging.getLogger("docuchat.ask")

def retrieve(tenant, question: str, top_k: int = 4) -> List[Dict]:
    cache_key = f"retrv:{tenant.id}:{hash(question)}:{top_k}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    qs = list(Chunk.objects.select_related("document")
        .only("id","text","document_id","tenant_id","page")
        .filter(tenant=tenant))
    if not qs:
        return []

    corpus = [(c.text or "") for c in qs]

    # TF-IDF similarity
    vectorizer = TfidfVectorizer(stop_words=None)
    tfidf = vectorizer.fit_transform(corpus + [question])
    tfidf_sims = cosine_similarity(tfidf[-1], tfidf[:-1]).flatten()

    # BM25 score
    tokenized = [re.findall(r"\w+", t.lower()) for t in corpus]
    bm25 = BM25Okapi(tokenized)
    bm25_scores = bm25.get_scores(re.findall(r"\w+", question.lower()))

    # Hybrid score
    import numpy as np
    hybrid = 0.40 * tfidf_sims + 0.60 * (bm25_scores / (max(bm25_scores)+1e-9))
    idxs = np.argsort(hybrid)[::-1][:max(top_k*3, top_k)]

    results: List[Dict] = []
    for i in idxs:
        c = qs[i]
        text = (c.text or "").strip()
        doc_obj = getattr(c, "document", None)
        doc_name = getattr(doc_obj, "filename", f"doc-{getattr(c, 'document_id','unknown')}")
        results.append({
            "doc": doc_name,
            "doc_id": getattr(doc_obj, "id", getattr(c, "document_id", None)),
            "page": getattr(c, "page", None),
            "chunk_id": c.id,
            "text": text,
            "snippet": (text[:280] + "…") if len(text) > 280 else text,
        })

    cache.set(cache_key, results[:top_k], 60)
    return results[:top_k]

_SENT_SPLIT = re.compile(r'(?<=[\.!?])\s+|\n+')

def _split_sentences(text: str):
    parts = [s.strip() for s in _SENT_SPLIT.split(text or "") if s.strip()]
    return parts or ([] if not text else [text.strip()])

def _score_sentence(q: str, s: str) -> float:
    ql, sl = q.lower(), s.lower()
    score = 0.0
    keys = re.findall(r'\w+', ql)
    for k in set(keys):
        if len(k) >= 4 and k in sl:
            score += 1.0
    if re.search(r'\b\d{1,2}\.\d{1,2}\.\d{4}\b', s):
        score += 2.0
    if re.search(r'\b20\d{2}\b', s):
        score += 0.5
    if re.search(r'\\b\\d+(?:\\.\\d+){1,3}\\b', s):  # 3.11.x gibi
        score += 1.2
    score -= min(len(s) / 500.0, 0.5)
    return score

def best_sentence_for_chunk(question: str, chunk_text: str) -> Optional[str]:
    sents = _split_sentences(chunk_text)
    if not sents:
        return None
    best_s, best_sc = None, float("-inf")
    for s in sents:
        sc = _score_sentence(question, s)
        if sc > best_sc:
            best_s, best_sc = s, sc
    return best_s.strip() if best_s else None

@api_view(["POST"])
def ask(request):
    tenant = getattr(request, "tenant", None)

    # Güvenli body okuma
    try:
        data = request.data or {}
    except Exception:
        return Response(
            {"answer": "Invalid JSON body.", "citations": []},
            status=status.HTTP_400_BAD_REQUEST,
        )

    q = (data.get("question") or "").strip() or (data.get("q") or "").strip()
    if not q:
        return Response({"answer": "Please provide a question.", "citations": []})

    try:
        top_k = int(getattr(settings, "TOP_K", 4))
    except Exception:
        top_k = 4

    try:
        # Retrieval
        raw_cites = retrieve(tenant, q, top_k=top_k)

        # Enrichment (quote önce)
        enriched = []
        for c in raw_cites:
            quote = best_sentence_for_chunk(q, c.get("text") or "")
            enriched.append({
                "doc": c["doc"],
                "doc_id": c["doc_id"],
                "page": c["page"],
                "chunk_id": c["chunk_id"],
                "snippet": c["snippet"],
                "quote": (quote or c["snippet"]),
            })

        # LLM seçimi
        llm_provider = getattr(settings, "LLM_PROVIDER", "gemini")
        use_gemini = (llm_provider == "gemini" and bool(getattr(settings, "GEMINI_API_KEY", "")))

        if use_gemini:
            ans = gemini_answer(q, enriched)
        else:
            ans = fake_llm_answer(q, enriched)

        # Nihai dönüş
        return Response({
            "answer": ans or "I don't know.",
            "citations": enriched,
        })

    except Exception as e:
        # Her durumda Response dön! (500 üretmeyelim)
        return Response(
            {"answer": f"Server error: {e}", "citations": []},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
def llm_health(_request):
    return Response(llm_healthcheck())
