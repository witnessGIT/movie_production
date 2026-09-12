from __future__ import annotations

import math
from typing import Any

import httpx


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return max(-1.0, min(1.0, dot / (na * nb)))


def embeddings(provider: str, model: str, texts: list[str], timeout: float = 8.0) -> list[list[float]] | None:
    if provider == "disabled" or not texts:
        return None
    try:
        with httpx.Client(timeout=timeout) as client:
            if provider == "ollama":
                response = client.post("http://127.0.0.1:11434/api/embed", json={"model": model, "input": texts})
                if response.status_code == 200:
                    data = response.json()
                    values = data.get("embeddings")
                    if isinstance(values, list) and len(values) == len(texts):
                        return values
                # Compatibility with older Ollama: one request per text.
                values = []
                for text in texts:
                    r = client.post("http://127.0.0.1:11434/api/embeddings", json={"model": model, "prompt": text})
                    if r.status_code != 200 or not isinstance(r.json().get("embedding"), list):
                        return None
                    values.append(r.json()["embedding"])
                return values
            if provider == "lmstudio":
                response = client.post("http://127.0.0.1:1234/v1/embeddings", json={"model": model, "input": texts})
                if response.status_code != 200:
                    return None
                rows = response.json().get("data") or []
                rows = sorted(rows, key=lambda x: x.get("index", 0))
                values = [row.get("embedding") for row in rows]
                return values if len(values) == len(texts) and all(isinstance(v, list) for v in values) else None
    except Exception:
        return None
    return None


def semantic_rerank(query: str, candidates: list[dict[str, Any]], provider: str, model: str) -> tuple[list[dict[str, Any]], bool]:
    if not candidates:
        return candidates, False
    texts = [query] + [str(c.get("text") or c.get("label") or "")[:4000] for c in candidates]
    vectors = embeddings(provider, model, texts)
    if not vectors:
        return candidates, False
    q = vectors[0]
    reranked = []
    for candidate, vector in zip(candidates, vectors[1:]):
        semantic = (_cosine(q, vector) + 1.0) / 2.0
        lexical = float(candidate.get("score") or 0.0)
        combined = lexical * 0.55 + semantic * 0.45
        reranked.append({**candidate, "embedding_score": round(semantic, 4), "score": round(combined, 4)})
    reranked.sort(key=lambda x: x.get("score", 0), reverse=True)
    return reranked, True


def chat(provider: str, model: str, prompt: str, timeout: float = 30.0) -> str | None:
    if provider == "disabled":
        return None
    try:
        with httpx.Client(timeout=timeout) as client:
            if provider == "ollama":
                r = client.post("http://127.0.0.1:11434/api/generate", json={"model": model, "prompt": prompt, "stream": False})
                return r.json().get("response", "").strip() if r.status_code == 200 else None
            if provider == "lmstudio":
                r = client.post("http://127.0.0.1:1234/v1/chat/completions", json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2})
                if r.status_code == 200:
                    return r.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip() or None
    except Exception:
        return None
    return None
