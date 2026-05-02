"""End-to-end tests for the full sec-rss-daily pipeline.

These tests mock all external HTTP calls so they run offline without any
API keys.  They exercise ``main()`` end-to-end, verifying that a Markdown
report is written and the deduplication archive is updated.
"""

import datetime as dt
import importlib
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Ensure scripts/ is importable
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_OPML = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <body>
    <outline text="Test Feed" title="Test Feed" xmlUrl="https://testfeed.example.com/rss"/>
  </body>
</opml>"""

MINIMAL_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Security Feed</title>
    <item>
      <title>Critical RCE in ExampleLib CVE-2024-9999</title>
      <link>https://blog.example.com/rce-2024</link>
      <description>A critical remote code execution vulnerability was found in ExampleLib.</description>
    </item>
    <item>
      <title>Ransomware Campaign Targets Healthcare</title>
      <link>https://blog.example.com/ransomware-healthcare</link>
      <description>A new ransomware group is targeting hospitals worldwide.</description>
    </item>
  </channel>
</rss>"""


def _make_response(content: bytes | str, status: int = 200) -> MagicMock:
    """Build a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status
    if isinstance(content, bytes):
        resp.content = content
        resp.text = content.decode("utf-8")
    else:
        resp.content = content.encode("utf-8")
        resp.text = content
    resp.raise_for_status = MagicMock()
    return resp


def _make_config(tmp_path: Path, *, ai_enabled: bool = False) -> Path:
    """Write a minimal skill.yaml to *tmp_path* and return its path."""
    cfg = {
        "pipeline": {
            "rss_fetch": {
                "enabled": True,
                "opml_url": "https://raw.githubusercontent.com/test/test/main/tiny.opml",
                "max_feeds": 5,
                "max_entries_per_feed": 5,
            },
            "dedup_and_time_filter": {
                "enabled": True,
                "since_hours": 9999,  # accept everything
                "seen_penalty": 5,
            },
            "fulltext_fetch": {"enabled": False, "timeout_seconds": 5},
            "ai_enrichment": {
                "enabled": ai_enabled,
                "provider": "openai-compatible",
                "model": "gpt-4o-mini",
                "endpoint_env": "AI_ENDPOINT",
                "api_key_env": "AI_API_KEY",
                "model_env": "AI_MODEL",
                "max_items": 10,
                "timeout_seconds": 10,
                "categories": ["漏洞通告", "攻击事件", "威胁情报", "其他"],
            },
            "cve_aggregation": {
                "enabled": True,
                "semantic_cluster": {"enabled": True, "eps": 0.75, "min_samples": 1},
            },
        },
        "output": {
            "markdown_dir": str(tmp_path / "output"),
            "report_name_format": "sec-daily-{date}.md",
            "archive_json_path": str(tmp_path / "data" / "seen_items.json"),
            "timezone": "UTC",
        },
    }
    config_path = tmp_path / "skill.yaml"
    config_path.write_text(yaml.dump(cfg), encoding="utf-8")
    return config_path


def _make_prompt(tmp_path: Path) -> Path:
    prompt_path = tmp_path / "ai_enrich_system.md"
    prompt_path.write_text("You are a security analyst. Output JSON.", encoding="utf-8")
    return prompt_path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reload_module():
    """Re-import the module fresh for each test to avoid state pollution."""
    if "generate_sec_daily" in sys.modules:
        del sys.modules["generate_sec_daily"]
    yield
    if "generate_sec_daily" in sys.modules:
        del sys.modules["generate_sec_daily"]


# ---------------------------------------------------------------------------
# E2E: heuristic-only run (no AI)
# ---------------------------------------------------------------------------

class TestE2EPipelineHeuristicOnly:
    def test_report_file_created(self, tmp_path):
        config_path = _make_config(tmp_path, ai_enabled=False)
        prompt_path = _make_prompt(tmp_path)

        def fake_get(url, **kwargs):
            if "opml" in url.lower() or "tiny.opml" in url:
                return _make_response(MINIMAL_OPML)
            return _make_response(MINIMAL_RSS)

        import generate_sec_daily as mod

        with patch("requests.Session") as MockSession:
            session = MagicMock()
            session.get.side_effect = fake_get
            MockSession.return_value = session

            with patch(
                "sys.argv",
                [
                    "generate_sec_daily.py",
                    "--config", str(config_path),
                    "--system-prompt", str(prompt_path),
                    "--date", "2024-01-01",
                ],
            ):
                mod.main()

        report = tmp_path / "output" / "sec-daily-2024-01-01.md"
        assert report.exists(), "Markdown report was not created"

    def test_report_contains_expected_sections(self, tmp_path):
        config_path = _make_config(tmp_path, ai_enabled=False)
        prompt_path = _make_prompt(tmp_path)

        def fake_get(url, **kwargs):
            if "opml" in url.lower() or "tiny.opml" in url:
                return _make_response(MINIMAL_OPML)
            return _make_response(MINIMAL_RSS)

        import generate_sec_daily as mod

        with patch("requests.Session") as MockSession:
            session = MagicMock()
            session.get.side_effect = fake_get
            MockSession.return_value = session

            with patch(
                "sys.argv",
                [
                    "generate_sec_daily.py",
                    "--config", str(config_path),
                    "--system-prompt", str(prompt_path),
                    "--date", "2024-01-01",
                ],
            ):
                mod.main()

        content = (tmp_path / "output" / "sec-daily-2024-01-01.md").read_text()
        assert "今日重点" in content
        assert "漏洞事件聚合" in content
        assert "分类统计" in content

    def test_report_contains_rce_article(self, tmp_path):
        config_path = _make_config(tmp_path, ai_enabled=False)
        prompt_path = _make_prompt(tmp_path)

        def fake_get(url, **kwargs):
            if "opml" in url.lower() or "tiny.opml" in url:
                return _make_response(MINIMAL_OPML)
            return _make_response(MINIMAL_RSS)

        import generate_sec_daily as mod

        with patch("requests.Session") as MockSession:
            session = MagicMock()
            session.get.side_effect = fake_get
            MockSession.return_value = session

            with patch(
                "sys.argv",
                [
                    "generate_sec_daily.py",
                    "--config", str(config_path),
                    "--system-prompt", str(prompt_path),
                    "--date", "2024-01-01",
                ],
            ):
                mod.main()

        content = (tmp_path / "output" / "sec-daily-2024-01-01.md").read_text()
        assert "CVE-2024-9999" in content

    def test_seen_archive_created(self, tmp_path):
        config_path = _make_config(tmp_path, ai_enabled=False)
        prompt_path = _make_prompt(tmp_path)

        def fake_get(url, **kwargs):
            if "opml" in url.lower() or "tiny.opml" in url:
                return _make_response(MINIMAL_OPML)
            return _make_response(MINIMAL_RSS)

        import generate_sec_daily as mod

        with patch("requests.Session") as MockSession:
            session = MagicMock()
            session.get.side_effect = fake_get
            MockSession.return_value = session

            with patch(
                "sys.argv",
                [
                    "generate_sec_daily.py",
                    "--config", str(config_path),
                    "--system-prompt", str(prompt_path),
                    "--date", "2024-01-01",
                ],
            ):
                mod.main()

        archive = tmp_path / "data" / "seen_items.json"
        assert archive.exists(), "seen_items.json was not created"
        data = json.loads(archive.read_text())
        assert isinstance(data, dict)
        assert len(data) >= 1

    def test_seen_penalty_applied_on_second_run(self, tmp_path):
        config_path = _make_config(tmp_path, ai_enabled=False)
        prompt_path = _make_prompt(tmp_path)

        def fake_get(url, **kwargs):
            if "opml" in url.lower() or "tiny.opml" in url:
                return _make_response(MINIMAL_OPML)
            return _make_response(MINIMAL_RSS)

        import generate_sec_daily as mod

        def run(date: str):
            with patch("requests.Session") as MockSession:
                session = MagicMock()
                session.get.side_effect = fake_get
                MockSession.return_value = session
                with patch(
                    "sys.argv",
                    [
                        "generate_sec_daily.py",
                        "--config", str(config_path),
                        "--system-prompt", str(prompt_path),
                        "--date", date,
                    ],
                ):
                    mod.main()

        run("2024-01-01")
        run("2024-01-02")

        content2 = (tmp_path / "output" / "sec-daily-2024-01-02.md").read_text()
        assert "历史重复" in content2


# ---------------------------------------------------------------------------
# E2E: AI-enriched run
# ---------------------------------------------------------------------------

AI_RESPONSE_PAYLOAD = json.dumps({
    "score": 92,
    "category": "漏洞通告",
    "summary_zh": "ExampleLib存在严重远程代码执行漏洞。",
    "translation_zh": "ExampleLib存在严重远程代码执行漏洞。",
    "tags": ["RCE", "CVE-2024-9999"],
    "reason": "高危RCE漏洞，评分提升",
})

AI_HTTP_RESPONSE = {
    "choices": [{"message": {"content": AI_RESPONSE_PAYLOAD}}]
}


class TestE2EPipelineWithAI:
    def test_ai_summary_appears_in_report(self, tmp_path, monkeypatch):
        config_path = _make_config(tmp_path, ai_enabled=True)
        prompt_path = _make_prompt(tmp_path)

        monkeypatch.setenv("AI_API_KEY", "test-key")
        monkeypatch.setenv("AI_ENDPOINT", "https://api.example.com/v1/chat/completions")

        def fake_get(url, **kwargs):
            if "opml" in url.lower() or "tiny.opml" in url:
                return _make_response(MINIMAL_OPML)
            return _make_response(MINIMAL_RSS)

        def fake_post(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json.return_value = AI_HTTP_RESPONSE
            return resp

        import generate_sec_daily as mod

        with patch("requests.Session") as MockSession:
            session = MagicMock()
            session.get.side_effect = fake_get
            session.post.side_effect = fake_post
            MockSession.return_value = session

            with patch(
                "sys.argv",
                [
                    "generate_sec_daily.py",
                    "--config", str(config_path),
                    "--system-prompt", str(prompt_path),
                    "--date", "2024-01-01",
                ],
            ):
                mod.main()

        content = (tmp_path / "output" / "sec-daily-2024-01-01.md").read_text()
        assert "ExampleLib存在严重远程代码执行漏洞" in content

    def test_ai_failure_falls_back_gracefully(self, tmp_path, monkeypatch):
        """When the AI endpoint returns an error, fallback enrichment should be used."""
        import requests as req_mod

        config_path = _make_config(tmp_path, ai_enabled=True)
        prompt_path = _make_prompt(tmp_path)

        monkeypatch.setenv("AI_API_KEY", "test-key")
        monkeypatch.setenv("AI_ENDPOINT", "https://api.example.com/v1/chat/completions")

        def fake_get(url, **kwargs):
            if "opml" in url.lower() or "tiny.opml" in url:
                return _make_response(MINIMAL_OPML)
            return _make_response(MINIMAL_RSS)

        def fake_post(url, **kwargs):
            raise req_mod.RequestException("Connection refused")

        import generate_sec_daily as mod

        with patch("requests.Session") as MockSession:
            session = MagicMock()
            session.get.side_effect = fake_get
            session.post.side_effect = fake_post
            MockSession.return_value = session

            with patch(
                "sys.argv",
                [
                    "generate_sec_daily.py",
                    "--config", str(config_path),
                    "--system-prompt", str(prompt_path),
                    "--date", "2024-01-01",
                ],
            ):
                mod.main()

        report = tmp_path / "output" / "sec-daily-2024-01-01.md"
        assert report.exists()
        content = report.read_text()
        assert "今日重点" in content


# ---------------------------------------------------------------------------
# E2E: edge cases
# ---------------------------------------------------------------------------

class TestE2EEdgeCases:
    def test_opml_fetch_failure_raises(self, tmp_path):
        """If the OPML URL is unreachable, the pipeline should propagate the error."""
        import requests as req_mod

        config_path = _make_config(tmp_path, ai_enabled=False)
        prompt_path = _make_prompt(tmp_path)

        def fake_get(url, **kwargs):
            raise req_mod.RequestException("Network error")

        import generate_sec_daily as mod

        with patch("requests.Session") as MockSession:
            session = MagicMock()
            session.get.side_effect = fake_get
            MockSession.return_value = session

            with patch(
                "sys.argv",
                [
                    "generate_sec_daily.py",
                    "--config", str(config_path),
                    "--system-prompt", str(prompt_path),
                    "--date", "2024-01-01",
                ],
            ):
                with pytest.raises(req_mod.RequestException):
                    mod.main()

    def test_empty_rss_feed_produces_report(self, tmp_path):
        """An empty RSS feed (no items) should still produce a valid report."""
        empty_rss = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Empty</title></channel></rss>"""

        config_path = _make_config(tmp_path, ai_enabled=False)
        prompt_path = _make_prompt(tmp_path)

        def fake_get(url, **kwargs):
            if "opml" in url.lower() or "tiny.opml" in url:
                return _make_response(MINIMAL_OPML)
            return _make_response(empty_rss)

        import generate_sec_daily as mod

        with patch("requests.Session") as MockSession:
            session = MagicMock()
            session.get.side_effect = fake_get
            MockSession.return_value = session

            with patch(
                "sys.argv",
                [
                    "generate_sec_daily.py",
                    "--config", str(config_path),
                    "--system-prompt", str(prompt_path),
                    "--date", "2024-01-01",
                ],
            ):
                mod.main()

        report = tmp_path / "output" / "sec-daily-2024-01-01.md"
        assert report.exists()

    def test_individual_feed_failure_does_not_abort_pipeline(self, tmp_path):
        """A failing individual feed should be silently skipped."""
        import requests as req_mod

        opml_two_feeds = """<?xml version="1.0"?>
<opml version="2.0">
  <body>
    <outline text="Good Feed" xmlUrl="https://good.example.com/rss"/>
    <outline text="Bad Feed" xmlUrl="https://bad.example.com/rss"/>
  </body>
</opml>"""

        config_path = _make_config(tmp_path, ai_enabled=False)
        prompt_path = _make_prompt(tmp_path)

        def fake_get(url, **kwargs):
            if "opml" in url.lower() or "tiny.opml" in url:
                return _make_response(opml_two_feeds)
            if "bad.example.com" in url:
                raise req_mod.RequestException("Bad feed unreachable")
            return _make_response(MINIMAL_RSS)

        import generate_sec_daily as mod

        with patch("requests.Session") as MockSession:
            session = MagicMock()
            session.get.side_effect = fake_get
            MockSession.return_value = session

            with patch(
                "sys.argv",
                [
                    "generate_sec_daily.py",
                    "--config", str(config_path),
                    "--system-prompt", str(prompt_path),
                    "--date", "2024-01-01",
                ],
            ):
                mod.main()  # must not raise

        report = tmp_path / "output" / "sec-daily-2024-01-01.md"
        assert report.exists()
