# sec-rss-skills

基于 RSS 源聚合每日热点的信息安全资讯，并按固定技能流程输出 Markdown 日报。

**符合 [agentskills.io](https://agentskills.io/specification) 规范** — 与 hermes-agent、openclaw 等 AI 代理兼容。

## 流程编排

本仓库不是仅靠提示词约束，而是通过脚本对流程进行固定编排：

1. RSS 抓取（支持 OPML 源）
2. 去重 + 时间过滤
3. 历史存档惩罚（已见内容默认 -5 分）
4. 可选全文抓取
5. AI 评分 + 分类 + 摘要 + 翻译（失败自动降级为启发式）
6. 漏洞事件聚合（CVE 匹配 + 语义聚类）
7. 渲染 Markdown 日报

## agentskills.io 规范支持

本项目遵循 [agentskills.io 规范](https://agentskills.io/specification)：

- ✅ **标准 SKILL.md**：包含必需的 YAML frontmatter（`name`、`description`）
- ✅ **目录命名一致**：技能目录名称与 `name` 字段匹配
- ✅ **代理兼容性**：支持 hermes-agent、openclaw 等符合规范的 AI 代理
- ✅ **渐进式披露**：元数据、指令、资源三级加载优化

详细技能文档：[skills/sec-rss-daily/SKILL.md](/skills/sec-rss-daily/SKILL.md)

## 仓库结构

```text
.
├── scripts/
│   └── generate_sec_daily.py      # 主流程脚本
├── skills/
│   └── sec-rss-daily/
│       ├── SKILL.md               # agentskills.io 标准技能文档
│       ├── skill.yaml             # 运行时配置（非标准，用于流程编排）
│       └── run.sh                 # Skill 执行入口
├── prompts/
│   └── ai_enrich_system.md        # AI 输出约束模板
├── data/
│   └── seen_items.json            # 历史归档（运行后生成/更新）
├── output/                        # Markdown 日报输出目录
├── requirements.txt
└── LICENSE                        # MIT 许可证
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
