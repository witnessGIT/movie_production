from app.source_discovery import discover


def test_search_template_discovery_encodes_query():
    rows = discover(
        ["日本央行 利率"],
        [{"id": "demo", "label": "Demo", "kind": "search_template", "url": "https://example.com/search?q={query}", "enabled": True}],
    )
    assert len(rows) == 1
    assert rows[0]["kind"] == "search_link"
    assert rows[0]["source_label"] == "Demo"
    assert "%E6%97%A5%E6%9C%AC" in rows[0]["url"]


def test_disabled_source_is_ignored():
    rows = discover(["news"], [{"id": "off", "label": "Off", "kind": "search_template", "url": "https://example.com/{query}", "enabled": False}])
    assert rows == []
