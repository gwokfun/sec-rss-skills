# sec-rss-daily Skill

这个 Skill 通过固定流程脚本化实现安全资讯日报，不依赖“纯提示词”执行：

1. RSS 抓取（OPML）
2. 去重 + 时间过滤
3. 历史归档惩罚（已见内容默认 -5 分）
4. 可选全文抓取
5. AI 评分 + 分类 + 中文摘要/翻译（可降级启发式）
6. 漏洞事件聚合（CVE 匹配 + 语义聚类）
7. Markdown 日报渲染输出

## 执行

```bash
bash skills/sec-rss-daily/run.sh
```

## 配置

主配置文件：`skills/sec-rss-daily/skill.yaml`

可配置项包括：
- RSS 源和抓取规模
- 时间窗口与重复惩罚
- 全文抓取开关
- AI 模型与端点（OpenAI 兼容）
- CVE 聚类参数
- 输出目录与文件命名
