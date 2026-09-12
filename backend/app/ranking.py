from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable


def tokens(text: str) -> list[str]:
    text = (text or "").lower()
    latin = re.findall(r"[a-z0-9]{2,}", text)
    cjk = re.findall(r"[\u3400-\u9fff]", text)
    bigrams = ["".join(cjk[i:i+2]) for i in range(max(0, len(cjk)-1))]
    return latin + bigrams


def lexical_score(query: str, text: str) -> float:
    q = Counter(tokens(query))
    d = Counter(tokens(text))
    if not q or not d:
        return 0.0
    overlap = sum(min(q[k], d[k]) for k in q)
    return min(1.0, overlap / max(1, sum(q.values())))


def quality_score(candidate: dict) -> float:
    score = 0.5
    w, h = candidate.get("width"), candidate.get("height")
    if w and h:
        pixels = w * h
        score += min(0.25, math.log10(max(pixels, 1)) / 30)
    duration = float(candidate.get("duration") or 0)
    if 2 <= duration <= 20:
        score += 0.15
    return min(1.0, score)


def rank_candidates(shots: list[dict], candidates: Iterable[dict], top_n: int = 3) -> list[dict]:
    pool = list(candidates)
    ranked: list[dict] = []
    used: set[tuple] = set()
    for shot in shots:
        voiceover = shot.get("voiceover", "")
        scored = []
        for candidate in pool:
            key = (candidate.get("asset_id"), candidate.get("start"), candidate.get("end"))
            semantic = lexical_score(voiceover, candidate.get("text", "") + " " + candidate.get("label", ""))
            quality = quality_score(candidate)
            diversity = 0.0 if key in used else 0.08
            score = round(semantic * 0.72 + quality * 0.20 + diversity, 4)
            scored.append({**candidate, "score": score, "semantic_score": round(semantic, 4), "quality_score": round(quality, 4)})
        scored.sort(key=lambda x: x["score"], reverse=True)
        best = scored[:top_n]
        if best:
            b = best[0]
            used.add((b.get("asset_id"), b.get("start"), b.get("end")))
        ranked.append({"shot": shot, "candidates": best})
    return ranked
