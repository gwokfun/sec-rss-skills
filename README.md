# sec-rss-skills

基于 RSS 源聚合每日热点的信息安全资讯，并按固定技能流程输出 Markdown 日报。

**符合 [agentskills.io](https://agentskills.io/specification) 规范** — 以 **Hermes-agent** 作为 skills 调用的底座 agent。

## 流程编排

本仓库不是仅靠提示词约束，而是通过脚本对流程进行固定编排：

1. RSS 抓取（支持 OPML 源）
2. 去重 + 时间过滤
3. 历史存档惩罚（已见内容默认 -5 分）
4. 可选全文抓取
5. AI 评分 + 分类 + 摘要 + 翻译（失败自动降级为启发式）
6. 漏洞事件聚合（CVE 匹配 + 语义聚类）
7. 渲染 Markdown 日报

## 重构设计方案

本次重构围绕两个原则展开：

1. **Skill 自包含**：`SKILL.md`、脚本、prompt、运行配置全部收敛到 `skills/sec-rss-daily/` 目录内，避免对仓库根目录执行上下文产生依赖。
2. **Hermes-agent 优先**：以 Hermes-agent 作为默认的 skills 调用底座，其他 agentskills.io 兼容代理只需复用同一份 `SKILL.md` 与 `run.sh` 契约。

对应的落地方案如下：

- `run.sh` 仅暴露 skill 入口，不再依赖切换到仓库根目录执行
- `generate_sec_daily.py` 默认按 skill 目录解析 `skill.yaml` 与 prompt
- `skill.yaml` 中的相对输出路径按配置文件所在目录解析，生成产物归档到 skill 工作区
- 仓库说明与 skill 文档统一以 Hermes-agent 为主调用方式

## agentskills.io 规范支持

本项目遵循 [agentskills.io 规范](https://agentskills.io/specification)：

- ✅ **标准 SKILL.md**：包含必需的 YAML frontmatter（`name`、`description`）
- ✅ **目录命名一致**：技能目录名称与 `name` 字段匹配
- ✅ **Hermes-agent 底座**：默认按 Hermes-agent 的 skill 发现与调用方式组织
- ✅ **渐进式披露**：元数据、指令、资源三级加载优化

详细技能文档：[skills/sec-rss-daily/SKILL.md](/skills/sec-rss-daily/SKILL.md)

## 仓库结构

```text
.
├── skills/
│   └── sec-rss-daily/
│       ├── SKILL.md               # agentskills.io 标准技能文档
│       ├── skill.yaml             # 运行时配置（非标准，用于流程编排）
│       ├── run.sh                 # Hermes-agent 调用入口
│       ├── scripts/
│       │   └── generate_sec_daily.py
│       ├── prompts/
│       │   └── ai_enrich_system.md
│       ├── data/                  # 运行后生成/更新
│       └── output/                # Markdown 日报输出目录
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

- `skills/sec-rss-daily/output/sec-daily-YYYY-MM-DD.md`

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

## Hermes-agent 调用方式

Hermes-agent 发现到 `skills/sec-rss-daily/SKILL.md` 后，按 skill 标准入口执行：

```bash
bash skills/sec-rss-daily/run.sh
```

默认情况下，skill 会在自己的目录下读取配置与 prompt，并将日报与归档文件写入 skill 工作区。
