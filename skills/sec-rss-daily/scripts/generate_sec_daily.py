#!/usr/bin/env python3
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import textwrap
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer


CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)
HIGH_VALUE_KEYWORDS = {
    "rce": 20,
    "0day": 18,
    "zero-day": 18,
    "exploit": 15,
    "勒索": 16,
    "ransomware": 16,
    "supply chain": 12,
    "apt": 10,
    "cve": 12,
}


@dataclass
class NewsItem:
    source: str
    feed_url: str
    title: str
    link: str
    published_at: dt.datetime | None
    summary: str
    full_text: str = ""
    key: str = ""
    cves: list[str] = field(default_factory=list)
    base_score: int = 0
    seen_before: bool = False
    final_score: int = 0
    category: str = "其他"
    ai_summary_zh: str = ""
    ai_translation_zh: str = ""
    tags: list[str] = field(default_factory=list)
    score_reason: str = ""


def to_raw_github_url(url: str) -> str:
    if "github.com" not in url or "/blob/" not in url:
        return url
    return url.replace("https://github.com/", "https://raw.githubusercontent.com/").replace("/blob/", "/")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    filtered_qs = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
    cleaned = parsed._replace(query=urlencode(filtered_qs), fragment="")
    return urlunparse(cleaned)


def item_key(title: str, link: str) -> str:
    raw = f"{title.strip().lower()}|{normalize_url(link).strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_datetime(value: Any) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = date_parser.parse(str(value))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def extract_feeds_from_opml(opml_text: str) -> list[tuple[str, str]]:
    feeds: list[tuple[str, str]] = []
    try:
        root = ET.fromstring(opml_text)
    except ET.ParseError:
        return feeds
    for outline in root.findall(".//outline"):
        xml_url = outline.attrib.get("xmlUrl")
        if not xml_url:
            continue
        title = outline.attrib.get("title") or outline.attrib.get("text") or xml_url
        feeds.append((title.strip(), xml_url.strip()))
    return feeds


def fetch_opml_feeds(session: requests.Session, opml_url: str, timeout: int = 20) -> list[tuple[str, str]]:
    url = to_raw_github_url(opml_url)
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    return extract_feeds_from_opml(resp.text)


def fetch_feed_entries(session: requests.Session, source_name: str, feed_url: str, max_entries: int) -> list[NewsItem]:
    entries: list[NewsItem] = []
    try:
        resp = session.get(feed_url, timeout=20)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
    except requests.RequestException:
        return entries

    for entry in parsed.entries[:max_entries]:
        title = str(getattr(entry, "title", "")).strip()
        link = str(getattr(entry, "link", "")).strip()
        if not title and not link:
            continue
        summary = str(getattr(entry, "summary", "")).strip()
        published = parse_datetime(getattr(entry, "published", None) or getattr(entry, "updated", None))
        key = item_key(title, link)
        cves = sorted({c.upper() for c in CVE_PATTERN.findall(f"{title} {summary}")})
        entries.append(
            NewsItem(
                source=source_name,
                feed_url=feed_url,
                title=title or "(无标题)",
                link=normalize_url(link),
                published_at=published,
                summary=strip_html(summary),
                key=key,
                cves=cves,
            )
        )
    return entries


def strip_html(text: str) -> str:
    if not text:
        return ""
    if "<" not in text and ">" not in text:
        return " ".join(text.split())
    soup = BeautifulSoup(text, "html.parser")
    return " ".join(soup.get_text(" ", strip=True).split())


def heuristic_base_score(item: NewsItem) -> int:
    text = f"{item.title} {item.summary}".lower()
    score = 35
    for kw, weight in HIGH_VALUE_KEYWORDS.items():
        if kw in text:
            score += weight
    score += min(20, len(item.cves) * 8)
    return max(0, min(100, score))


def optional_fetch_full_text(session: requests.Session, item: NewsItem, timeout_sec: int) -> None:
    if not item.link:
        return
    try:
        resp = session.get(item.link, timeout=timeout_sec)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        text = "\n".join([p for p in paragraphs if p])
        item.full_text = textwrap.shorten(text, width=6000, placeholder="...")
    except requests.RequestException:
        return


def load_seen_map(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data
    return {}


def save_seen_map(path: Path, seen_map: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(seen_map, f, ensure_ascii=False, indent=2)


def parse_json_payload(raw_text: str) -> dict[str, Any] | None:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
        return None
    except json.JSONDecodeError:
        return None


def ai_enrich_item(
    session: requests.Session,
    item: NewsItem,
    system_prompt: str,
    categories: list[str],
    endpoint: str,
    api_key: str,
    model: str,
    timeout_sec: int,
) -> None:
    body = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "categories": categories,
                        "title": item.title,
                        "url": item.link,
                        "published_at": item.published_at.isoformat() if item.published_at else None,
                        "summary": item.summary,
                        "full_text": item.full_text[:4000],
                        "cves": item.cves,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        resp = session.post(endpoint, headers=headers, json=body, timeout=timeout_sec)
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
    except (requests.RequestException, KeyError, IndexError, ValueError, TypeError):
        return

    payload = parse_json_payload(raw)
    if not payload:
        return

    category = str(payload.get("category", "其他")).strip()
    item.category = category if category in categories else "其他"
    try:
        item.final_score = int(payload.get("score", item.base_score))
    except (ValueError, TypeError):
        item.final_score = item.base_score
    item.final_score = max(0, min(100, item.final_score))
    item.ai_summary_zh = str(payload.get("summary_zh", "")).strip()
    item.ai_translation_zh = str(payload.get("translation_zh", "")).strip()
    raw_tags = payload.get("tags", [])
    if isinstance(raw_tags, list):
        item.tags = [str(x).strip() for x in raw_tags if str(x).strip()][:5]
    item.score_reason = str(payload.get("reason", "")).strip()


def fallback_enrich(item: NewsItem, categories: list[str]) -> None:
    if item.cves:
        category = "漏洞通告"
    elif "ransom" in item.title.lower() or "勒索" in item.title:
        category = "攻击事件"
    elif "apt" in item.title.lower() or "threat" in item.title.lower():
        category = "威胁情报"
    else:
        category = "其他"
    item.category = category if category in categories else "其他"
    item.final_score = item.base_score
    item.ai_summary_zh = item.summary[:180] if item.summary else item.title
    item.ai_translation_zh = item.ai_summary_zh
    item.tags = item.cves[:3]
    item.score_reason = "启发式评分（未使用AI）"


def apply_seen_penalty(item: NewsItem, seen_map: dict[str, dict[str, Any]], penalty: int) -> None:
    if item.key in seen_map:
        item.seen_before = True
        item.final_score = max(0, item.final_score - penalty)


def semantic_cluster(items: list[NewsItem], eps: float, min_samples: int) -> dict[int, list[NewsItem]]:
    if not items:
        return {}
    texts = [f"{it.title} {it.summary} {it.ai_summary_zh}" for it in items]
    if all(not t.strip() for t in texts):
        return {idx: [it] for idx, it in enumerate(items)}
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(texts)
    model = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine")
    labels = model.fit_predict(matrix)
    grouped: dict[int, list[NewsItem]] = {}
    for label, item in zip(labels, items):
        grouped.setdefault(int(label), []).append(item)
    return grouped


def aggregate_cve_events(items: list[NewsItem]) -> dict[str, Any]:
    cve_map: dict[str, list[NewsItem]] = {}
    for item in items:
        for cve in item.cves:
            cve_map.setdefault(cve, []).append(item)

    result: dict[str, Any] = {"by_cve": cve_map, "clusters": {}}
    vuln_items = [it for it in items if it.cves or it.category == "漏洞通告"]
    if vuln_items:
        clusters = semantic_cluster(vuln_items, eps=0.75, min_samples=1)
        result["clusters"] = clusters
    return result


def render_markdown(
    report_date: dt.date,
    items: list[NewsItem],
    cve_events: dict[str, Any],
    since_hours: int,
) -> str:
    lines: list[str] = []
    lines.append(f"# 网络安全资讯日报 - {report_date.isoformat()}")
    lines.append("")
    lines.append(f"- 时间窗口: 最近 {since_hours} 小时")
    lines.append(f"- 入选条目: {len(items)}")
    lines.append("")

    lines.append("## 今日重点")
    lines.append("")
    for idx, item in enumerate(items[:20], 1):
        pub = item.published_at.isoformat() if item.published_at else "未知时间"
        summary = item.ai_summary_zh or item.summary or item.title
        tags = f" [{', '.join(item.tags)}]" if item.tags else ""
        seen = " (历史重复)" if item.seen_before else ""
        lines.append(f"{idx}. [{item.title}]({item.link})")
        lines.append(f"   - 分类: {item.category} | 评分: {item.final_score}{seen}{tags}")
        lines.append(f"   - 来源: {item.source} | 发布时间: {pub}")
        lines.append(f"   - 摘要: {summary}")
        if item.ai_translation_zh and item.ai_translation_zh != summary:
            lines.append(f"   - 翻译: {item.ai_translation_zh}")
    lines.append("")

    lines.append("## 漏洞事件聚合")
    lines.append("")
    by_cve: dict[str, list[NewsItem]] = cve_events.get("by_cve", {})
    if not by_cve:
        lines.append("- 今日未匹配到明确CVE事件。")
    else:
        for cve, related in sorted(by_cve.items(), key=lambda kv: len(kv[1]), reverse=True)[:30]:
            lines.append(f"- **{cve}**：关联 {len(related)} 条")
            for rel in related[:4]:
                lines.append(f"  - [{rel.title}]({rel.link})")
    lines.append("")

    clusters: dict[int, list[NewsItem]] = cve_events.get("clusters", {})
    lines.append("## 语义簇观察")
    lines.append("")
    if not clusters:
        lines.append("- 无可聚类漏洞主题。")
    else:
        sorted_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)
        for idx, (_, cluster_items) in enumerate(sorted_clusters[:10], 1):
            top = sorted(cluster_items, key=lambda x: x.final_score, reverse=True)[:3]
            seed_title = top[0].title if top else "未知主题"
            lines.append(f"- 主题 {idx}: {seed_title}（{len(cluster_items)} 条）")
            for it in top:
                lines.append(f"  - [{it.title}]({it.link})")
    lines.append("")

    lines.append("## 分类统计")
    lines.append("")
    category_count: dict[str, int] = {}
    for it in items:
        category_count[it.category] = category_count.get(it.category, 0) + 1
    for name, count in sorted(category_count.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"- {name}: {count}")

    lines.append("")
    lines.append("---")
    lines.append("由 sec-rss-daily skill 自动生成")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate security RSS daily markdown report")
    parser.add_argument("--config", default="skills/sec-rss-daily/skill.yaml", help="Skill config YAML path")
    parser.add_argument("--system-prompt", default="skills/sec-rss-daily/prompts/ai_enrich_system.md", help="AI system prompt path")
    parser.add_argument("--date", default=None, help="Report date, format YYYY-MM-DD")
    args = parser.parse_args()

    root = Path.cwd()
    config_path = root / args.config
    prompt_path = root / args.system_prompt
    cfg = load_yaml(config_path)

    p_fetch = cfg["pipeline"]["rss_fetch"]
    p_filter = cfg["pipeline"]["dedup_and_time_filter"]
    p_fulltext = cfg["pipeline"]["fulltext_fetch"]
    p_ai = cfg["pipeline"]["ai_enrichment"]
    p_cve = cfg["pipeline"]["cve_aggregation"]
    out_cfg = cfg["output"]

    report_date = dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(dt.timezone.utc).date()
    since_hours = int(p_filter.get("since_hours", 24))
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=since_hours)

    session = requests.Session()
    session.headers.update({"User-Agent": "sec-rss-daily/1.0"})

    opml_url = p_fetch.get("opml_url", "")
    if not opml_url:
        raise ValueError("pipeline.rss_fetch.opml_url is not set in config")
    feeds = fetch_opml_feeds(session, opml_url)
    feeds = feeds[: int(p_fetch.get("max_feeds", 100))]

    all_items: list[NewsItem] = []
    for source_name, feed_url in feeds:
        all_items.extend(fetch_feed_entries(session, source_name, feed_url, int(p_fetch.get("max_entries_per_feed", 15))))

    # 去重：同key仅保留发布时间更新的一条
    uniq: dict[str, NewsItem] = {}
    for item in all_items:
        prev = uniq.get(item.key)
        if prev is None:
            uniq[item.key] = item
        else:
            prev_ts = prev.published_at or dt.datetime.fromtimestamp(0, tz=dt.timezone.utc)
            curr_ts = item.published_at or dt.datetime.fromtimestamp(0, tz=dt.timezone.utc)
            if curr_ts > prev_ts:
                uniq[item.key] = item

    filtered = [
        it for it in uniq.values() if (it.published_at is None or it.published_at >= cutoff)
    ]

    archive_path = root / out_cfg["archive_json_path"]
    seen_map = load_seen_map(archive_path)

    for item in filtered:
        item.base_score = heuristic_base_score(item)
        item.final_score = item.base_score

    if p_fulltext.get("enabled", False):
        for item in filtered:
            optional_fetch_full_text(session, item, int(p_fulltext.get("timeout_seconds", 8)))

    categories = p_ai.get("categories", ["其他"])
    ai_enabled = bool(p_ai.get("enabled", False))
    api_key = os.getenv(str(p_ai.get("api_key_env", "AI_API_KEY")), "")
    endpoint = os.getenv(str(p_ai.get("endpoint_env", "AI_ENDPOINT")), "https://api.openai.com/v1/chat/completions")
    model = os.getenv(str(p_ai.get("model_env", "AI_MODEL")), str(p_ai.get("model", "gpt-4o-mini")))

    system_prompt = ""
    if prompt_path.exists():
        system_prompt = prompt_path.read_text(encoding="utf-8")

    ai_max = int(p_ai.get("max_items", 80))
    for item in sorted(filtered, key=lambda x: x.base_score, reverse=True)[:ai_max]:
        if ai_enabled and api_key and system_prompt:
            ai_enrich_item(
                session=session,
                item=item,
                system_prompt=system_prompt,
                categories=categories,
                endpoint=endpoint,
                api_key=api_key,
                model=model,
                timeout_sec=int(p_ai.get("timeout_seconds", 30)),
            )
            if item.final_score == item.base_score and not item.ai_summary_zh:
                fallback_enrich(item, categories)
        else:
            fallback_enrich(item, categories)

    # 对没有进入AI处理窗口的条目进行兜底处理
    enriched_keys = {it.key for it in sorted(filtered, key=lambda x: x.base_score, reverse=True)[:ai_max]}
    for item in filtered:
        if item.key not in enriched_keys:
            fallback_enrich(item, categories)

    penalty = int(p_filter.get("seen_penalty", 5))
    for item in filtered:
        apply_seen_penalty(item, seen_map, penalty)

    filtered.sort(key=lambda x: x.final_score, reverse=True)

    cve_events = aggregate_cve_events(filtered) if p_cve.get("enabled", True) else {"by_cve": {}, "clusters": {}}

    md = render_markdown(report_date, filtered, cve_events, since_hours=since_hours)
    markdown_dir = root / out_cfg["markdown_dir"]
    markdown_dir.mkdir(parents=True, exist_ok=True)
    report_name = out_cfg["report_name_format"].format(date=report_date.isoformat())
    report_path = markdown_dir / report_name
    report_path.write_text(md, encoding="utf-8")

    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
    for item in filtered:
        seen_map[item.key] = {
            "title": item.title,
            "link": item.link,
            "last_seen_at": now_iso,
            "source": item.source,
        }
    save_seen_map(archive_path, seen_map)

    print(f"Report generated: {report_path}")
    print(f"Items after filter: {len(filtered)}")


if __name__ == "__main__":
    main()
