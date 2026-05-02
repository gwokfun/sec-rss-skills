# sec-rss-skills

基于 RSS 源聚合每日热点的信息安全资讯，并按固定技能流程输出 Markdown 日报。

## 流程编排

本仓库不是仅靠提示词约束，而是通过脚本对流程进行固定编排：

1. RSS 抓取（支持 OPML 源）
2. 去重 + 时间过滤
3. 历史存档惩罚（已见内容默认 -5 分）
4. 可选全文抓取
5. AI 评分 + 分类 + 摘要 + 翻译（失败自动降级为启发式）
6. 漏洞事件聚合（CVE 匹配 + 语义聚类）
7. 渲染 Markdown 日报

## 仓库结构

```text
.
├── scripts/
│   └── generate_sec_daily.py      # 主流程脚本
├── skills/
│   └── sec-rss-daily/
│       ├── skill.yaml             # Skill 编排配置
│       ├── run.sh                 # Skill 执行入口
│       └── SKILL.md               # Skill 说明
├── prompts/
│   └── ai_enrich_system.md        # AI 输出约束模板
├── data/
│   └── seen_items.json            # 历史归档（运行后生成/更新）
├── output/                        # Markdown 日报输出目录
└── requirements.txt
```

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 运行

```bash
bash skills/sec-rss-daily/run.sh
```

默认 RSS 源配置为：

- https://github.com/zer0yu/CyberSecurityRSS/blob/master/tiny.opml

输出示例：

- `output/sec-daily-YYYY-MM-DD.md`

## AI 模型配置（可选）

支持 OpenAI 兼容接口。未配置时自动使用启发式规则完成分类和摘要。

```bash
export AI_API_KEY="<your-api-key>"
export AI_ENDPOINT="https://api.openai.com/v1/chat/completions"
export AI_MODEL="gpt-4o-mini"
```

可在 `skills/sec-rss-daily/skill.yaml` 中调整：

- 抓取规模与时间窗口
- 历史惩罚分值
- 全文抓取开关
- AI 开关和分类体系
- CVE 聚类参数
- 输出目录和命名
