---
name: sec-rss-daily
version: "1.0.0"
description: Use this skill to generate daily security RSS digest reports in Markdown format. The skill aggregates security news from RSS feeds, scores and categorizes them using AI or heuristics, clusters vulnerability events, and outputs a comprehensive daily report. Use when the user wants to create security news digests, aggregate CVE information, or generate automated security briefings.
author: gwokfun
license: MIT
compatibility: Requires Python 3.9+, sqlite (optional), and dependencies from requirements.txt. Optional AI API key for enhanced scoring and categorization.
apis:
  - run(date?: string): markdown_file
inputs:
  date:
    type: string
    required: false
    description: "Report date in YYYY-MM-DD format. Defaults to today (UTC)."
  config:
    type: string
    required: false
    description: "Path to skill.yaml config file. Defaults to skill.yaml in this skill directory."
  system_prompt:
    type: string
    required: false
    description: "Path to AI system prompt file. Defaults to prompts/ai_enrich_system.md in this skill directory."
  AI_API_KEY:
    type: env_var
    required: false
    description: "API key for OpenAI-compatible endpoint. If unset, heuristic fallback is used."
  AI_ENDPOINT:
    type: env_var
    required: false
    description: "OpenAI-compatible chat completions endpoint URL."
  AI_MODEL:
    type: env_var
    required: false
    description: "Model name to use for AI enrichment (e.g. gpt-4o-mini)."
outputs:
  report:
    type: file
    description: "Markdown report written to skills/sec-rss-daily/output/sec-daily-YYYY-MM-DD.md"
  archive:
    type: file
    description: "Deduplication archive updated at skills/sec-rss-daily/data/seen_items.json"
metadata:
  tech_stack: python3, scikit-learn, feedparser
  agents: hermes-agent
---

# sec-rss-daily Skill

This skill generates automated daily security news digests by orchestrating a fixed pipeline of RSS aggregation, AI-powered analysis, and vulnerability event clustering.

## When to Use This Skill

Use this skill when you need to:
- Generate daily security news reports from RSS feeds
- Aggregate and prioritize cybersecurity news articles
- Cluster and analyze CVE (Common Vulnerabilities and Exposures) information
- Create Markdown-formatted security briefings
- Monitor security RSS sources with deduplication and scoring

## How It Works

This skill implements a scripted pipeline (not purely prompt-based) with the following stages:

1. **RSS Fetching**: Reads OPML feed lists and fetches entries from multiple security RSS sources
2. **Deduplication & Time Filtering**: Removes duplicate entries and filters by time window (default: 24 hours)
3. **Historical Penalty**: Applies scoring penalty to previously seen items (-5 points by default)
4. **Optional Full-Text Fetch**: Can retrieve full article content for deeper analysis
5. **AI Enrichment**: Uses OpenAI-compatible API to score (0-100), categorize, summarize in Chinese, and tag articles. Falls back to heuristic rules if AI is unavailable
6. **CVE Aggregation**: Matches CVE identifiers and performs semantic clustering of vulnerability-related news
7. **Markdown Rendering**: Outputs a structured daily report with top items, CVE aggregations, semantic clusters, and category statistics

## Execution

To run this skill, execute:

```bash
bash skills/sec-rss-daily/run.sh
```

This will:
- Load configuration from `skills/sec-rss-daily/skill.yaml`
- Execute the main pipeline script at `skills/sec-rss-daily/scripts/generate_sec_daily.py`
- Output a Markdown report to `skills/sec-rss-daily/output/sec-daily-YYYY-MM-DD.md`
- Update the deduplication archive at `skills/sec-rss-daily/data/seen_items.json`

## Configuration

The skill is configured via `skills/sec-rss-daily/skill.yaml` (separate from this SKILL.md standard file).

**Note**: The `skill.yaml` file is a runtime configuration file specific to this implementation, not part of the agentskills.io standard. It controls:

- **RSS Sources**: OPML URL and fetch limits
- **Time Window**: Hours to look back (default: 24)
- **Deduplication**: Penalty for previously seen items (default: -5 points)
- **Full-Text Fetch**: Enable/disable and timeout settings
- **AI Configuration**: API endpoint, model, categories, and item limits
- **CVE Clustering**: Semantic clustering parameters (DBSCAN eps, min_samples)
- **Output**: Directory, filename format, timezone

## AI Model Configuration (Optional)

The skill works with or without AI. For enhanced scoring and categorization, configure:

```bash
export AI_API_KEY="your-api-key"
export AI_ENDPOINT="https://api.openai.com/v1/chat/completions"
export AI_MODEL="gpt-4o-mini"
```

Without AI configuration, the skill automatically falls back to heuristic scoring based on keywords and CVE presence.

## Default RSS Source

The default configuration uses:
- **OPML URL**: https://github.com/zer0yu/CyberSecurityRSS/blob/master/tiny.opml

This provides a curated list of Chinese and international cybersecurity RSS feeds.

## Output Format

The generated Markdown report includes:

1. **Today's Highlights**: Top 20 scored items with category, score, tags, source, and summaries
2. **CVE Aggregation**: CVE identifiers with related articles
3. **Semantic Clusters**: Grouped vulnerability topics discovered through ML clustering
4. **Category Statistics**: Distribution of items across security categories

Categories include:
- 漏洞通告 (Vulnerability Announcements)
- 威胁情报 (Threat Intelligence)
- 攻击事件 (Attack Incidents)
- 安全研究 (Security Research)
- 工具与产品 (Tools & Products)
- 政策与合规 (Policy & Compliance)
- 其他 (Other)

## Agent Compatibility

This skill is designed to work with:
- **hermes-agent**: Primary/base agent for skill discovery and invocation
- **Any agentskills.io-compatible agent**: Reuse the same `SKILL.md` and `run.sh` contract after Hermes-agent validation

## Files Structure

```
skills/sec-rss-daily/
├── SKILL.md              # This file (agentskills.io standard)
├── skill.yaml            # Pipeline configuration (not part of standard)
├── run.sh                # Hermes-agent execution entry point
├── scripts/
│   └── generate_sec_daily.py  # Main pipeline implementation
├── prompts/
│   └── ai_enrich_system.md    # AI system prompt template
├── data/
│   └── seen_items.json        # Historical deduplication archive (generated)
└── output/
    └── sec-daily-*.md         # Generated reports (created after run)
```

## Example Usage for Agents

When an agent detects a user request like:
- "Generate today's security news digest"
- "Create a daily cybersecurity briefing"
- "Aggregate recent CVE information from RSS feeds"
- "What are the top security news today?"

Hermes-agent should invoke this skill by executing the `run.sh` script and then present or process the generated Markdown output.

## Customization

To customize the skill behavior, edit `skills/sec-rss-daily/skill.yaml`:

- Change RSS sources by modifying `pipeline.rss_fetch.opml_url`
- Adjust time window with `pipeline.dedup_and_time_filter.since_hours`
- Enable full-text extraction with `pipeline.fulltext_fetch.enabled: true`
- Modify AI categories in `pipeline.ai_enrichment.categories`
- Tune CVE clustering sensitivity via `pipeline.cve_aggregation.semantic_cluster.eps`

## Dependencies

Install required Python packages:

```bash
pip install -r requirements.txt
```

Required packages:
- feedparser (RSS parsing)
- requests (HTTP client)
- beautifulsoup4 (HTML parsing)
- PyYAML (configuration)
- scikit-learn (semantic clustering)
- python-dateutil (date parsing)
