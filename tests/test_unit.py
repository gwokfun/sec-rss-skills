"""Unit tests for scripts/generate_sec_daily.py"""

import datetime as dt
import sys
from pathlib import Path

import pytest

# Ensure the scripts directory is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from generate_sec_daily import (  # noqa: E402
    NewsItem,
    aggregate_cve_events,
    apply_seen_penalty,
    extract_feeds_from_opml,
    fallback_enrich,
    heuristic_base_score,
    item_key,
    normalize_url,
    parse_datetime,
    parse_json_payload,
    render_markdown,
    strip_html,
    to_raw_github_url,
)


# ---------------------------------------------------------------------------
# normalize_url
# ---------------------------------------------------------------------------

class TestNormalizeUrl:
    def test_removes_utm_params(self):
        url = "https://example.com/article?utm_source=feed&utm_medium=rss&id=42"
        result = normalize_url(url)
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "id=42" in result

    def test_removes_fragment(self):
        url = "https://example.com/page#section"
        assert normalize_url(url) == "https://example.com/page"

    def test_empty_string_returns_empty(self):
        assert normalize_url("") == ""

    def test_url_without_tracking_unchanged(self):
        url = "https://example.com/article?id=1&ref=home"
        result = normalize_url(url)
        assert "id=1" in result
        assert "ref=home" in result

    def test_none_returns_empty(self):
        assert normalize_url(None) == ""  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# to_raw_github_url
# ---------------------------------------------------------------------------

class TestToRawGithubUrl:
    def test_converts_blob_url(self):
        url = "https://github.com/owner/repo/blob/main/file.opml"
        expected = "https://raw.githubusercontent.com/owner/repo/main/file.opml"
        assert to_raw_github_url(url) == expected

    def test_non_github_url_unchanged(self):
        url = "https://example.com/file.opml"
        assert to_raw_github_url(url) == url

    def test_github_without_blob_unchanged(self):
        url = "https://github.com/owner/repo"
        assert to_raw_github_url(url) == url


# ---------------------------------------------------------------------------
# item_key
# ---------------------------------------------------------------------------

class TestItemKey:
    def test_same_title_and_link_produces_same_key(self):
        assert item_key("Title A", "https://example.com") == item_key("Title A", "https://example.com")

    def test_different_title_different_key(self):
        assert item_key("Title A", "https://example.com") != item_key("Title B", "https://example.com")

    def test_case_insensitive_title(self):
        assert item_key("TITLE", "https://example.com") == item_key("title", "https://example.com")

    def test_utm_stripped_from_link(self):
        key1 = item_key("T", "https://example.com?utm_source=rss")
        key2 = item_key("T", "https://example.com")
        assert key1 == key2

    def test_returns_64_char_hex(self):
        k = item_key("hello", "https://example.com")
        assert len(k) == 64
        assert all(c in "0123456789abcdef" for c in k)


# ---------------------------------------------------------------------------
# parse_datetime
# ---------------------------------------------------------------------------

class TestParseDatetime:
    def test_parses_iso_string(self):
        result = parse_datetime("2024-01-15T10:30:00Z")
        assert isinstance(result, dt.datetime)
        assert result.tzinfo == dt.timezone.utc

    def test_returns_none_for_empty(self):
        assert parse_datetime("") is None
        assert parse_datetime(None) is None

    def test_returns_none_for_invalid(self):
        assert parse_datetime("not-a-date") is None

    def test_naive_datetime_becomes_utc(self):
        result = parse_datetime("2024-01-15 10:30:00")
        assert result is not None
        assert result.tzinfo == dt.timezone.utc

    def test_tz_aware_converted_to_utc(self):
        result = parse_datetime("2024-01-15T10:30:00+08:00")
        assert result is not None
        assert result.hour == 2  # 10:30 CST = 02:30 UTC


# ---------------------------------------------------------------------------
# extract_feeds_from_opml
# ---------------------------------------------------------------------------

SAMPLE_OPML = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <body>
    <outline text="Feed A" title="Feed A" xmlUrl="https://feed-a.example.com/rss"/>
    <outline text="Feed B" xmlUrl="https://feed-b.example.com/atom"/>
    <outline text="No URL"/>
  </body>
</opml>"""


class TestExtractFeedsFromOpml:
    def test_extracts_feeds(self):
        feeds = extract_feeds_from_opml(SAMPLE_OPML)
        assert len(feeds) == 2
        assert feeds[0] == ("Feed A", "https://feed-a.example.com/rss")
        assert feeds[1] == ("Feed B", "https://feed-b.example.com/atom")

    def test_skips_outlines_without_xmlurl(self):
        feeds = extract_feeds_from_opml(SAMPLE_OPML)
        titles = [t for t, _ in feeds]
        assert "No URL" not in titles

    def test_invalid_xml_returns_empty(self):
        feeds = extract_feeds_from_opml("<not valid xml>>>")
        assert feeds == []

    def test_empty_opml_returns_empty(self):
        opml = """<opml version="2.0"><body></body></opml>"""
        assert extract_feeds_from_opml(opml) == []

    def test_uses_text_attribute_as_fallback_name(self):
        opml = """<opml><body><outline text="By Text" xmlUrl="https://x.com/rss"/></body></opml>"""
        feeds = extract_feeds_from_opml(opml)
        assert feeds[0][0] == "By Text"


# ---------------------------------------------------------------------------
# strip_html
# ---------------------------------------------------------------------------

class TestStripHtml:
    def test_strips_html_tags(self):
        html = "<p>Hello <strong>world</strong>!</p>"
        assert strip_html(html) == "Hello world !"

    def test_plain_text_unchanged(self):
        assert strip_html("plain text") == "plain text"

    def test_empty_string(self):
        assert strip_html("") == ""

    def test_collapses_whitespace(self):
        result = strip_html("  multiple   spaces  ")
        assert "  " not in result

    def test_html_with_no_text_returns_empty(self):
        assert strip_html("<br/><hr/>") == ""


# ---------------------------------------------------------------------------
# heuristic_base_score
# ---------------------------------------------------------------------------

def _make_item(**kwargs) -> NewsItem:
    defaults = dict(
        source="test",
        feed_url="https://example.com/rss",
        title="",
        link="https://example.com/1",
        published_at=None,
        summary="",
    )
    defaults.update(kwargs)
    return NewsItem(**defaults)


class TestHeuristicBaseScore:
    def test_baseline_score_is_35(self):
        item = _make_item(title="boring news", summary="nothing interesting")
        assert heuristic_base_score(item) == 35

    def test_rce_keyword_increases_score(self):
        item = _make_item(title="Critical RCE vulnerability found", summary="")
        score = heuristic_base_score(item)
        assert score > 35

    def test_cve_in_list_increases_score(self):
        item = _make_item(title="patched", summary="", cves=["CVE-2024-1234"])
        score = heuristic_base_score(item)
        assert score > 35

    def test_score_capped_at_100(self):
        item = _make_item(
            title="RCE 0day zero-day exploit ransomware apt supply chain cve 勒索",
            summary="cve rce 0day zero-day",
            cves=["CVE-2024-1", "CVE-2024-2", "CVE-2024-3"],
        )
        assert heuristic_base_score(item) <= 100

    def test_score_minimum_is_0(self):
        item = _make_item(title="", summary="")
        assert heuristic_base_score(item) >= 0


# ---------------------------------------------------------------------------
# parse_json_payload
# ---------------------------------------------------------------------------

class TestParseJsonPayload:
    def test_valid_json_object(self):
        result = parse_json_payload('{"score": 80, "category": "漏洞通告"}')
        assert result == {"score": 80, "category": "漏洞通告"}

    def test_json_array_returns_none(self):
        assert parse_json_payload("[1, 2, 3]") is None

    def test_invalid_json_returns_none(self):
        assert parse_json_payload("not json") is None

    def test_empty_string_returns_none(self):
        assert parse_json_payload("") is None

    def test_strips_markdown_code_fence(self):
        raw = "```json\n{\"score\": 50}\n```"
        result = parse_json_payload(raw)
        assert result == {"score": 50}

    def test_strips_backtick_fence_without_language(self):
        raw = "```\n{\"key\": \"value\"}\n```"
        result = parse_json_payload(raw)
        assert result == {"key": "value"}


# ---------------------------------------------------------------------------
# fallback_enrich
# ---------------------------------------------------------------------------

CATEGORIES = ["漏洞通告", "威胁情报", "攻击事件", "安全研究", "其他"]


class TestFallbackEnrich:
    def test_cve_sets_vuln_category(self):
        item = _make_item(title="patch released", summary="", cves=["CVE-2024-0001"])
        fallback_enrich(item, CATEGORIES)
        assert item.category == "漏洞通告"

    def test_ransom_keyword_sets_attack(self):
        item = _make_item(title="New ransomware campaign", summary="")
        fallback_enrich(item, CATEGORIES)
        assert item.category == "攻击事件"

    def test_apt_keyword_sets_threat(self):
        item = _make_item(title="APT group targets banks", summary="")
        fallback_enrich(item, CATEGORIES)
        assert item.category == "威胁情报"

    def test_unknown_falls_back_to_other(self):
        item = _make_item(title="generic security post", summary="nothing")
        fallback_enrich(item, CATEGORIES)
        assert item.category == "其他"

    def test_final_score_set_to_base_score(self):
        item = _make_item(title="test", summary="")
        item.base_score = 55
        fallback_enrich(item, CATEGORIES)
        assert item.final_score == 55

    def test_summary_used_for_ai_summary(self):
        item = _make_item(title="T", summary="A brief description")
        fallback_enrich(item, CATEGORIES)
        assert item.ai_summary_zh == "A brief description"

    def test_cves_become_tags(self):
        item = _make_item(title="patch", summary="", cves=["CVE-2024-1", "CVE-2024-2"])
        fallback_enrich(item, CATEGORIES)
        assert item.tags == ["CVE-2024-1", "CVE-2024-2"]

    def test_category_not_in_list_falls_to_other(self):
        item = _make_item(title="勒索软件攻击", summary="")
        fallback_enrich(item, ["其他"])  # 攻击事件 not in list
        assert item.category == "其他"


# ---------------------------------------------------------------------------
# apply_seen_penalty
# ---------------------------------------------------------------------------

class TestApplySeenPenalty:
    def test_penalty_applied_to_seen_item(self):
        item = _make_item(title="old news", summary="")
        item.key = "abc123"
        item.final_score = 60
        seen_map = {"abc123": {"title": "old news", "link": "https://x.com"}}
        apply_seen_penalty(item, seen_map, penalty=10)
        assert item.seen_before is True
        assert item.final_score == 50

    def test_no_penalty_for_unseen_item(self):
        item = _make_item(title="new news", summary="")
        item.key = "newkey"
        item.final_score = 60
        apply_seen_penalty(item, {}, penalty=10)
        assert item.seen_before is False
        assert item.final_score == 60

    def test_score_does_not_go_below_zero(self):
        item = _make_item(title="old", summary="")
        item.key = "k"
        item.final_score = 3
        apply_seen_penalty(item, {"k": {}}, penalty=10)
        assert item.final_score == 0


# ---------------------------------------------------------------------------
# aggregate_cve_events
# ---------------------------------------------------------------------------

class TestAggregateCveEvents:
    def test_empty_list_returns_empty(self):
        result = aggregate_cve_events([])
        assert result["by_cve"] == {}

    def test_cve_grouping(self):
        item1 = _make_item(title="report1", summary="", cves=["CVE-2024-1111"])
        item2 = _make_item(title="report2", summary="", cves=["CVE-2024-1111", "CVE-2024-2222"])
        result = aggregate_cve_events([item1, item2])
        assert len(result["by_cve"]["CVE-2024-1111"]) == 2
        assert len(result["by_cve"]["CVE-2024-2222"]) == 1

    def test_items_without_cves_not_in_by_cve(self):
        item = _make_item(title="no cve", summary="")
        result = aggregate_cve_events([item])
        assert result["by_cve"] == {}


# ---------------------------------------------------------------------------
# render_markdown
# ---------------------------------------------------------------------------

class TestRenderMarkdown:
    def _make_enriched_item(self, title: str, score: int = 50) -> NewsItem:
        item = _make_item(
            title=title,
            summary="test summary",
            link="https://example.com/article",
        )
        item.final_score = score
        item.category = "安全研究"
        item.ai_summary_zh = "测试摘要"
        item.published_at = dt.datetime(2024, 1, 15, 0, 0, tzinfo=dt.timezone.utc)
        return item

    def test_contains_report_date(self):
        items = [self._make_enriched_item("Test item")]
        md = render_markdown(dt.date(2024, 1, 15), items, {"by_cve": {}, "clusters": {}}, since_hours=24)
        assert "2024-01-15" in md

    def test_contains_item_title(self):
        items = [self._make_enriched_item("My Security Article")]
        md = render_markdown(dt.date(2024, 1, 15), items, {"by_cve": {}, "clusters": {}}, since_hours=24)
        assert "My Security Article" in md

    def test_no_cve_shows_placeholder(self):
        md = render_markdown(dt.date(2024, 1, 15), [], {"by_cve": {}, "clusters": {}}, since_hours=24)
        assert "未匹配到明确CVE事件" in md

    def test_since_hours_shown(self):
        md = render_markdown(dt.date(2024, 1, 15), [], {"by_cve": {}, "clusters": {}}, since_hours=48)
        assert "48" in md

    def test_category_statistics_section_present(self):
        items = [self._make_enriched_item("T")]
        md = render_markdown(dt.date(2024, 1, 15), items, {"by_cve": {}, "clusters": {}}, since_hours=24)
        assert "分类统计" in md

    def test_cve_listed_when_present(self):
        item = self._make_enriched_item("CVE article")
        item.cves = ["CVE-2024-9999"]
        events = aggregate_cve_events([item])
        md = render_markdown(dt.date(2024, 1, 15), [item], events, since_hours=24)
        assert "CVE-2024-9999" in md

    def test_item_count_in_header(self):
        items = [self._make_enriched_item(f"Item {i}") for i in range(3)]
        md = render_markdown(dt.date(2024, 1, 15), items, {"by_cve": {}, "clusters": {}}, since_hours=24)
        assert "入选条目: 3" in md
