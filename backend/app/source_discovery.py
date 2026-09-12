from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

import httpx

from .ranking import lexical_score


def _rss_items(url: str) -> list[dict]:
    try:
        with httpx.Client(timeout=8.0, follow_redirects=True, headers={"User-Agent": "MovieProduction/0.2"}) as client:
            r = client.get(url)
            if r.status_code != 200:
                return []
        root = ET.fromstring(r.text)
    except Exception:
        return []
    rows = []
    for item in root.findall(".//item")[:100]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()
        published = (item.findtext("pubDate") or "").strip()
        if title or link:
            rows.append({"title": title, "url": link, "description": description, "published": published})
    if rows:
        return rows
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//a:entry", ns)[:100]:
        title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
        link_node = entry.find("a:link", ns)
        link = link_node.attrib.get("href", "") if link_node is not None else ""
        summary = (entry.findtext("a:summary", default="", namespaces=ns) or "").strip()
        published = (entry.findtext("a:updated", default="", namespaces=ns) or "").strip()
        rows.append({"title": title, "url": link, "description": summary, "published": published})
    return rows


def discover(queries: list[str], sources: list[dict], max_per_source: int = 12) -> list[dict]:
    results: list[dict] = []
    for source in sources:
        if not source.get("enabled", True):
            continue
        kind = source.get("kind")
        label = source.get("label") or source.get("id") or "source"
        url = source.get("url", "")
        if kind == "rss" and url:
            scored = []
            for row in _rss_items(url):
                hay = f"{row.get('title','')} {row.get('description','')}"
                score = max([lexical_score(q, hay) for q in queries] or [0.0])
                scored.append({**row, "source_id": source.get("id"), "source_label": label, "score": round(score, 4), "kind": "article"})
            scored.sort(key=lambda x: x["score"], reverse=True)
            results.extend(scored[:max_per_source])
        elif kind == "search_template" and url:
            for query in queries[:8]:
                try:
                    search_url = url.format(query=quote_plus(query))
                except Exception:
                    continue
                results.append({"source_id": source.get("id"), "source_label": label, "kind": "search_link", "query": query, "url": search_url, "score": 0.0})
    return results
