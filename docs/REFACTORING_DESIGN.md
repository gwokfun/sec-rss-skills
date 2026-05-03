# sec-rss-skills 重构设计方案
# Refactoring Design for Hermes-Agent Integration

**版本**: 2.0.0
**日期**: 2026-05-03
**作者**: gwokfun
**目标**: 将 sec-rss-skills 重构为基于 Hermes-agent 的模块化技能框架

---

## 1. 执行摘要 (Executive Summary)

### 1.1 当前状态
- **架构**: 固定流程脚本化编排 (Scripted Pipeline)
- **技能模型**: 单一技能 (sec-rss-daily)，固定 7 步流水线
- **AI 集成**: 可选 OpenAI 兼容 API，失败时降级为启发式规则
- **代理兼容性**: 符合 agentskills.io 规范，但缺乏模块化和可扩展性

### 1.2 目标状态
- **架构**: 基于 Hermes-agent 的模块化技能框架
- **技能模型**: 可插拔技能模块，支持技能编排和链式调用
- **AI 集成**: 统一的 LLM 推理引擎，支持多模型策略
- **代理兼容性**: 增强的 Hermes-agent 原生支持，保持 agentskills.io 兼容性

### 1.3 核心收益
1. **模块化**: 每个流水线步骤独立为可重用技能
2. **可扩展性**: 轻松添加新技能（如实时监控、威胁情报分析）
3. **可组合性**: 技能可以独立使用或编排为工作流
4. **可测试性**: 每个技能单元测试，简化调试和维护
5. **灵活性**: 动态技能发现、热插拔、策略选择

---

## 2. 架构演进 (Architecture Evolution)

### 2.1 当前架构 (Current: v1.0.0)

```
┌─────────────────────────────────────────────────────────────────┐
│                         run.sh                                  │
│                   (Bash Entry Point)                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│               generate_sec_daily.py                             │
│           (527-line Monolithic Pipeline)                        │
│                                                                 │
│  1. RSS Fetch (OPML + Feeds)                                   │
│  2. Deduplication + Time Filter                                │
│  3. Historical Penalty                                         │
│  4. Optional Full-Text Fetch                                   │
│  5. AI Enrichment (with fallback)                              │
│  6. CVE Aggregation + Semantic Clustering                      │
│  7. Markdown Rendering                                         │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  Output Files  │
                    │  - .md report  │
                    │  - archive.json│
                    └────────────────┘
```

**问题**:
- ❌ 流程硬编码，无法灵活调整步骤
- ❌ 难以独立测试单个步骤
- ❌ AI 逻辑与业务逻辑耦合
- ❌ 无法重用流水线步骤构建其他技能
- ❌ 缺乏技能间通信和编排机制

---

### 2.2 目标架构 (Target: v2.0.0 with Hermes-Agent)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Hermes-Agent Core                                 │
│                   (Orchestrator + Context Manager)                       │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │   Skill Registry & Router   │
              │   (Dynamic Discovery)       │
              └──────────────┬──────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Core Skills    │  │ Pipeline Skills │  │ Composite Skill │
│  (Atomic)       │  │ (Orchestrators) │  │ (High-Level)    │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Core Skills (原子技能)                      │
├─────────────────────────────────────────────────────────────────┤
│  1. RSSFetchSkill          - RSS/OPML 抓取                      │
│  2. DeduplicationSkill     - 去重 + 时间过滤                    │
│  3. HistoricalPenaltySkill - 历史存档惩罚                       │
│  4. FullTextFetchSkill     - 全文抓取                           │
│  5. AIEnrichmentSkill      - AI 评分/分类/摘要                  │
│  6. HeuristicScoringSkill  - 启发式评分                         │
│  7. CVEAggregationSkill    - CVE 匹配聚合                       │
│  8. SemanticClusterSkill   - 语义聚类                           │
│  9. MarkdownRenderSkill    - Markdown 渲染                      │
│ 10. ArchiveManagerSkill    - 存档读写                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   Pipeline Skills (编排技能)                     │
├─────────────────────────────────────────────────────────────────┤
│  • SecRssDailyPipeline     - 完整日报流程 (组合 1-10)          │
│  • QuickScanPipeline       - 快速扫描 (仅 1,2,6,9)             │
│  • CVEMonitorPipeline      - CVE 专项监控 (1,2,7,8,9)          │
│  • RealTimeAlertPipeline   - 实时告警 (1,2,5,9)                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Shared Infrastructure                        │
├─────────────────────────────────────────────────────────────────┤
│  • LLMReasoningEngine      - 统一 LLM 调用接口                  │
│  • ContextManager          - 技能间上下文传递                   │
│  • ConfigRegistry          - 配置管理                           │
│  • SkillMetrics            - 性能监控                           │
│  • EventBus                - 技能事件发布订阅                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心设计决策 (Core Design Decisions)

### 3.1 技能接口标准 (Skill Interface Standard)

采用 **Hermes-Agent 技能接口模式**，所有技能实现统一接口:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class SkillContext:
    """技能执行上下文，用于技能间数据传递"""
    data: Dict[str, Any]           # 主要数据载荷
    metadata: Dict[str, Any]       # 元数据（时间戳、来源等）
    config: Dict[str, Any]         # 运行时配置
    history: List[str]             # 执行历史（用于调试）

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        self.data[key] = value

@dataclass
class SkillResult:
    """技能执行结果"""
    success: bool                  # 执行是否成功
    output: Any                    # 输出数据
    error: Optional[str] = None    # 错误信息
    metadata: Dict[str, Any] = None  # 结果元数据

class SkillInterface(ABC):
    """Hermes-Agent 技能基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """技能名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """技能描述"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """技能版本"""
        pass

    @abstractmethod
    def can_handle(self, query: str, context: SkillContext) -> bool:
        """判断是否能处理当前请求"""
        pass

    @abstractmethod
    def execute(self, context: SkillContext) -> SkillResult:
        """执行技能逻辑"""
        pass

    def get_parameters(self) -> Dict[str, Any]:
        """返回技能参数 schema（可选）"""
        return {}

    def validate(self, context: SkillContext) -> bool:
        """验证输入上下文（可选）"""
        return True
```

---

### 3.2 技能设计模式 (Skill Design Patterns)

#### 3.2.1 Chain of Responsibility (责任链模式)
- **用途**: 技能路由和动态发现
- **实现**: `SkillRouter` 遍历注册技能，调用 `can_handle()` 找到匹配技能

#### 3.2.2 Strategy Pattern (策略模式)
- **用途**: AI vs 启发式评分的策略切换
- **实现**: `ScoringStrategy` 接口，`AIScoringStrategy` 和 `HeuristicScoringStrategy` 实现

#### 3.2.3 Decorator Pattern (装饰器模式)
- **用途**: 技能执行的横切关注点（日志、缓存、重试）
- **实现**: `@retry_on_failure`, `@cache_result`, `@log_execution` 装饰器

#### 3.2.4 Pipeline/Chain Pattern (流水线模式)
- **用途**: 多步骤技能编排
- **实现**: `SkillPipeline` 类，按顺序执行技能列表，传递 context

#### 3.2.5 Observer Pattern (观察者模式)
- **用途**: 技能执行监控、日志、告警
- **实现**: `EventBus` 发布技能生命周期事件

---

### 3.3 LLM 推理引擎设计 (LLM Reasoning Engine)

统一的 LLM 调用层，支持多提供商和策略:

```python
from enum import Enum
from typing import Protocol

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    CUSTOM = "custom"

class LLMReasoningEngine:
    """统一 LLM 推理引擎"""

    def __init__(self, config: Dict[str, Any]):
        self.provider = config.get("provider", LLMProvider.OPENAI)
        self.model = config.get("model", "gpt-4o-mini")
        self.endpoint = config.get("endpoint")
        self.api_key = config.get("api_key")
        self.timeout = config.get("timeout", 30)
        self.max_retries = config.get("max_retries", 3)

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> str:
        """完成 LLM 推理调用"""
        # 统一接口，支持多提供商
        pass

    def complete_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """JSON 结构化输出"""
        pass

    def batch_complete(
        self,
        prompts: List[str],
        **kwargs
    ) -> List[str]:
        """批量推理（优化性能）"""
        pass
```

---

### 3.4 配置管理 (Configuration Management)

采用分层配置系统:

1. **全局配置** (`hermes_config.yaml`):
   - Hermes-agent 核心配置
   - LLM 提供商配置
   - 技能注册表

2. **技能配置** (`skills/*/skill_config.yaml`):
   - 技能特定参数
   - 依赖声明
   - 执行策略

3. **运行时配置** (环境变量):
   - API 密钥
   - 敏感信息
   - 环境特定覆盖

```yaml
# hermes_config.yaml (全局配置)
hermes:
  version: "2.0.0"
  log_level: INFO

llm_engine:
  default_provider: openai
  providers:
    openai:
      endpoint_env: AI_ENDPOINT
      api_key_env: AI_API_KEY
      model_env: AI_MODEL
      default_model: gpt-4o-mini
      timeout: 30
      max_retries: 3

skill_registry:
  auto_discover: true
  skill_paths:
    - skills/core
    - skills/pipelines

context_manager:
  max_history_size: 100
  enable_persistence: true

event_bus:
  enabled: true
  handlers:
    - logger
    - metrics_collector
```

---

## 4. 技能重构映射 (Skill Refactoring Mapping)

将现有单体流水线拆分为 10 个原子技能:

### 4.1 Core Skills (原子技能)

#### Skill 1: RSSFetchSkill
```python
class RSSFetchSkill(SkillInterface):
    name = "rss_fetch"
    description = "从 RSS/OPML 源抓取新闻条目"
    version = "2.0.0"

    def execute(self, context: SkillContext) -> SkillResult:
        opml_url = context.config.get("opml_url")
        max_feeds = context.config.get("max_feeds", 120)
        max_entries = context.config.get("max_entries_per_feed", 15)

        # 1. 获取 OPML 源列表
        feeds = self._fetch_opml_feeds(opml_url)

        # 2. 抓取每个源的条目
        items = []
        for feed in feeds[:max_feeds]:
            items.extend(self._fetch_feed_entries(feed, max_entries))

        # 3. 输出到 context
        context.set("raw_items", items)
        return SkillResult(success=True, output=items)
```

**输入**:
- `config.opml_url`: OPML 源 URL
- `config.max_feeds`: 最大源数量
- `config.max_entries_per_feed`: 每源最大条目数

**输出**:
- `context.raw_items`: List[NewsItem]

---

#### Skill 2: DeduplicationSkill
```python
class DeduplicationSkill(SkillInterface):
    name = "deduplication"
    description = "去重并按时间窗口过滤"
    version = "2.0.0"

    def execute(self, context: SkillContext) -> SkillResult:
        items = context.get("raw_items", [])
        since_hours = context.config.get("since_hours", 24)

        # 1. 去重（基于 SHA256 key）
        unique_items = self._deduplicate_by_key(items)

        # 2. 时间过滤
        cutoff = datetime.utcnow() - timedelta(hours=since_hours)
        filtered_items = [
            item for item in unique_items
            if item.published_at and item.published_at >= cutoff
        ]

        context.set("filtered_items", filtered_items)
        return SkillResult(success=True, output=filtered_items)
```

**输入**:
- `context.raw_items`: List[NewsItem]
- `config.since_hours`: 时间窗口（小时）

**输出**:
- `context.filtered_items`: List[NewsItem]

---

#### Skill 3: HistoricalPenaltySkill
```python
class HistoricalPenaltySkill(SkillInterface):
    name = "historical_penalty"
    description = "对历史存档中的条目施加评分惩罚"
    version = "2.0.0"

    def execute(self, context: SkillContext) -> SkillResult:
        items = context.get("filtered_items", [])
        archive_path = context.config.get("archive_path", "data/seen_items.json")
        penalty = context.config.get("seen_penalty", 5)

        # 1. 加载历史存档
        archive = self._load_archive(archive_path)

        # 2. 标记已见条目并施加惩罚
        for item in items:
            if item.key in archive:
                item.seen_before = True
                item.final_score = max(0, item.base_score - penalty)
            else:
                item.final_score = item.base_score

        context.set("penalized_items", items)
        return SkillResult(success=True, output=items)
```

**输入**:
- `context.filtered_items`: List[NewsItem]
- `config.archive_path`: 存档文件路径
- `config.seen_penalty`: 惩罚分数

**输出**:
- `context.penalized_items`: List[NewsItem]

---

#### Skill 4: FullTextFetchSkill
```python
class FullTextFetchSkill(SkillInterface):
    name = "fulltext_fetch"
    description = "抓取文章全文内容"
    version = "2.0.0"

    def execute(self, context: SkillContext) -> SkillResult:
        items = context.get("penalized_items", [])
        timeout = context.config.get("timeout_seconds", 8)

        # 并发抓取全文
        for item in items:
            try:
                item.full_text = self._fetch_full_text(item.link, timeout)
            except Exception as e:
                item.full_text = ""  # 失败时使用空字符串

        context.set("items_with_fulltext", items)
        return SkillResult(success=True, output=items)
```

**输入**:
- `context.penalized_items`: List[NewsItem]
- `config.timeout_seconds`: 超时时间

**输出**:
- `context.items_with_fulltext`: List[NewsItem]

---

#### Skill 5: AIEnrichmentSkill
```python
class AIEnrichmentSkill(SkillInterface):
    name = "ai_enrichment"
    description = "使用 LLM 进行评分、分类、摘要"
    version = "2.0.0"

    def __init__(self, llm_engine: LLMReasoningEngine):
        self.llm_engine = llm_engine

    def execute(self, context: SkillContext) -> SkillResult:
        items = context.get("items_with_fulltext", [])
        max_items = context.config.get("max_items", 80)
        categories = context.config.get("categories", [])

        # 按 base_score 排序，处理前 max_items
        sorted_items = sorted(items, key=lambda x: x.base_score, reverse=True)
        top_items = sorted_items[:max_items]

        # LLM 批量处理
        for item in top_items:
            try:
                enriched = self._enrich_with_ai(item, categories)
                item.final_score = enriched["score"]
                item.category = enriched["category"]
                item.ai_summary_zh = enriched["summary_zh"]
                item.ai_translation_zh = enriched["translation_zh"]
                item.tags = enriched["tags"]
                item.score_reason = enriched["reason"]
            except Exception as e:
                # AI 失败，跳过（由 HeuristicScoringSkill 补充）
                pass

        context.set("enriched_items", items)
        return SkillResult(success=True, output=items)
```

**依赖**:
- `LLMReasoningEngine`

**输入**:
- `context.items_with_fulltext`: List[NewsItem]
- `config.max_items`: 处理数量
- `config.categories`: 分类列表

**输出**:
- `context.enriched_items`: List[NewsItem]

---

#### Skill 6: HeuristicScoringSkill
```python
class HeuristicScoringSkill(SkillInterface):
    name = "heuristic_scoring"
    description = "启发式关键词评分和分类"
    version = "2.0.0"

    def execute(self, context: SkillContext) -> SkillResult:
        items = context.get("enriched_items", [])

        # 对未被 AI 处理的条目使用启发式
        for item in items:
            if not item.category or item.category == "其他":
                self._apply_heuristic_scoring(item)

        context.set("scored_items", items)
        return SkillResult(success=True, output=items)
```

**输入**:
- `context.enriched_items`: List[NewsItem]

**输出**:
- `context.scored_items`: List[NewsItem]

---

#### Skill 7: CVEAggregationSkill
```python
class CVEAggregationSkill(SkillInterface):
    name = "cve_aggregation"
    description = "按 CVE 聚合相关文章"
    version = "2.0.0"

    def execute(self, context: SkillContext) -> SkillResult:
        items = context.get("scored_items", [])

        # 按 CVE 分组
        cve_groups = self._group_by_cve(items)

        context.set("cve_groups", cve_groups)
        return SkillResult(success=True, output=cve_groups)
```

**输入**:
- `context.scored_items`: List[NewsItem]

**输出**:
- `context.cve_groups`: Dict[str, List[NewsItem]]

---

#### Skill 8: SemanticClusterSkill
```python
class SemanticClusterSkill(SkillInterface):
    name = "semantic_cluster"
    description = "基于 TF-IDF + DBSCAN 的语义聚类"
    version = "2.0.0"

    def execute(self, context: SkillContext) -> SkillResult:
        items = context.get("scored_items", [])
        eps = context.config.get("eps", 0.75)
        min_samples = context.config.get("min_samples", 1)

        # 语义聚类
        clusters = self._semantic_cluster(items, eps, min_samples)

        context.set("clusters", clusters)
        return SkillResult(success=True, output=clusters)
```

**输入**:
- `context.scored_items`: List[NewsItem]
- `config.eps`: DBSCAN epsilon
- `config.min_samples`: DBSCAN 最小样本数

**输出**:
- `context.clusters`: List[List[NewsItem]]

---

#### Skill 9: MarkdownRenderSkill
```python
class MarkdownRenderSkill(SkillInterface):
    name = "markdown_render"
    description = "渲染 Markdown 日报"
    version = "2.0.0"

    def execute(self, context: SkillContext) -> SkillResult:
        items = context.get("scored_items", [])
        cve_groups = context.get("cve_groups", {})
        clusters = context.get("clusters", [])

        # 渲染 4 个部分
        markdown = self._render_markdown(
            items=items,
            cve_groups=cve_groups,
            clusters=clusters,
            date=context.metadata.get("date")
        )

        context.set("markdown_report", markdown)
        return SkillResult(success=True, output=markdown)
```

**输入**:
- `context.scored_items`: List[NewsItem]
- `context.cve_groups`: Dict[str, List[NewsItem]]
- `context.clusters`: List[List[NewsItem]]

**输出**:
- `context.markdown_report`: str

---

#### Skill 10: ArchiveManagerSkill
```python
class ArchiveManagerSkill(SkillInterface):
    name = "archive_manager"
    description = "读写历史存档"
    version = "2.0.0"

    def execute(self, context: SkillContext) -> SkillResult:
        items = context.get("scored_items", [])
        archive_path = context.config.get("archive_path", "data/seen_items.json")
        output_path = context.config.get("output_path")
        markdown = context.get("markdown_report", "")

        # 1. 写入 Markdown 报告
        self._write_report(output_path, markdown)

        # 2. 更新存档
        self._update_archive(archive_path, items)

        return SkillResult(success=True, output={"report": output_path})
```

**输入**:
- `context.scored_items`: List[NewsItem]
- `context.markdown_report`: str
- `config.archive_path`: 存档路径
- `config.output_path`: 输出路径

**输出**:
- 文件写入成功状态

---

### 4.2 Pipeline Skills (编排技能)

#### SecRssDailyPipeline
```python
class SecRssDailyPipeline(SkillInterface):
    name = "sec_rss_daily_pipeline"
    description = "完整安全 RSS 日报流水线"
    version = "2.0.0"

    def __init__(self, skill_registry: SkillRegistry):
        self.pipeline = SkillPipeline([
            skill_registry.get("rss_fetch"),
            skill_registry.get("deduplication"),
            skill_registry.get("historical_penalty"),
            skill_registry.get("fulltext_fetch"),
            skill_registry.get("heuristic_scoring"),  # 先启发式打分
            skill_registry.get("ai_enrichment"),      # 再 AI 增强
            skill_registry.get("cve_aggregation"),
            skill_registry.get("semantic_cluster"),
            skill_registry.get("markdown_render"),
            skill_registry.get("archive_manager"),
        ])

    def execute(self, context: SkillContext) -> SkillResult:
        return self.pipeline.execute(context)
```

---

## 5. 实施计划 (Implementation Plan)

### 5.1 阶段 1: 基础设施 (Week 1-2)
- [ ] 创建 `SkillInterface`、`SkillContext`、`SkillResult` 基类
- [ ] 实现 `SkillRegistry` 和 `SkillRouter`
- [ ] 实现 `LLMReasoningEngine` 统一接口
- [ ] 实现 `ConfigManager` 分层配置
- [ ] 实现 `ContextManager` 上下文管理
- [ ] 实现 `EventBus` 事件系统
- [ ] 创建 `hermes_config.yaml` 全局配置

### 5.2 阶段 2: 核心技能迁移 (Week 3-4)
- [ ] 实现 10 个原子技能 (Skill 1-10)
- [ ] 为每个技能编写单元测试
- [ ] 验证技能独立性和可测试性
- [ ] 创建技能配置文件 (`skill_config.yaml`)

### 5.3 阶段 3: 流水线编排 (Week 5)
- [ ] 实现 `SkillPipeline` 编排器
- [ ] 实现 `SecRssDailyPipeline`
- [ ] 创建快速扫描、CVE 监控等其他流水线
- [ ] 编写 E2E 流水线测试

### 5.4 阶段 4: Hermes-Agent 集成 (Week 6)
- [ ] 创建 Hermes-Agent 主入口 (`hermes_agent.py`)
- [ ] 实现自然语言意图识别和技能路由
- [ ] 创建交互式 CLI 模式
- [ ] 更新 `SKILL.md` 为 Hermes-Agent 格式

### 5.5 阶段 5: 文档和工具 (Week 7)
- [ ] 更新 README.md
- [ ] 编写技能开发指南
- [ ] 创建技能模板生成器
- [ ] 编写迁移指南 (v1 → v2)

### 5.6 阶段 6: 兼容性和发布 (Week 8)
- [ ] 保持 agentskills.io 规范兼容性
- [ ] 创建 v1 兼容层 (可选)
- [ ] 性能优化和压力测试
- [ ] 发布 v2.0.0

---

## 6. 文件目录结构 (Directory Structure)

```
sec-rss-skills/                      # 项目根目录
├── hermes_config.yaml               # Hermes-Agent 全局配置
├── hermes_agent.py                  # Hermes-Agent 主入口
├── requirements.txt                 # Python 依赖
├── pyproject.toml                   # 项目配置
├── README.md                        # 项目文档
├── docs/
│   ├── REFACTORING_DESIGN.md       # 本设计文档
│   ├── SKILL_DEVELOPMENT_GUIDE.md  # 技能开发指南
│   └── MIGRATION_GUIDE.md          # v1→v2 迁移指南
├── hermes/                          # Hermes-Agent 核心框架
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── skill_interface.py      # 技能基类和接口
│   │   ├── skill_registry.py       # 技能注册表
│   │   ├── skill_router.py         # 技能路由器
│   │   ├── skill_pipeline.py       # 流水线编排器
│   │   ├── context_manager.py      # 上下文管理器
│   │   └── event_bus.py            # 事件总线
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── reasoning_engine.py     # LLM 推理引擎
│   │   ├── providers/
│   │   │   ├── openai_provider.py
│   │   │   ├── anthropic_provider.py
│   │   │   └── azure_provider.py
│   │   └── strategies/
│   │       ├── ai_scoring_strategy.py
│   │       └── heuristic_strategy.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── config_manager.py       # 配置管理器
│   │   └── config_validator.py     # 配置验证器
│   └── utils/
│       ├── __init__.py
│       ├── decorators.py           # 装饰器（retry, cache, log）
│       ├── metrics.py              # 性能监控
│       └── logger.py               # 日志工具
├── skills/                          # 技能目录
│   ├── core/                        # 原子技能
│   │   ├── rss_fetch/
│   │   │   ├── __init__.py
│   │   │   ├── skill.py            # RSSFetchSkill
│   │   │   ├── skill_config.yaml   # 技能配置
│   │   │   └── SKILL.md            # 技能文档
│   │   ├── deduplication/
│   │   │   ├── __init__.py
│   │   │   ├── skill.py
│   │   │   ├── skill_config.yaml
│   │   │   └── SKILL.md
│   │   ├── historical_penalty/
│   │   ├── fulltext_fetch/
│   │   ├── ai_enrichment/
│   │   ├── heuristic_scoring/
│   │   ├── cve_aggregation/
│   │   ├── semantic_cluster/
│   │   ├── markdown_render/
│   │   └── archive_manager/
│   └── pipelines/                   # 编排技能
│       ├── sec_rss_daily/
│       │   ├── __init__.py
│       │   ├── pipeline.py         # SecRssDailyPipeline
│       │   ├── skill_config.yaml
│       │   └── SKILL.md
│       ├── quick_scan/
│       ├── cve_monitor/
│       └── realtime_alert/
├── tests/                           # 测试目录
│   ├── unit/
│   │   ├── test_core_skills.py     # 核心技能单元测试
│   │   ├── test_llm_engine.py      # LLM 引擎测试
│   │   └── test_config.py          # 配置测试
│   ├── integration/
│   │   └── test_pipelines.py       # 流水线集成测试
│   └── e2e/
│       └── test_e2e.py              # 端到端测试
├── data/                            # 数据目录
│   └── seen_items.json              # 历史存档
├── output/                          # 输出目录
│   └── sec-daily-*.md               # 生成的报告
└── legacy/                          # v1 遗留代码（可选）
    └── generate_sec_daily.py        # v1 脚本（备份）
```

---

## 7. 配置文件示例 (Configuration Examples)

### 7.1 hermes_config.yaml (全局配置)

```yaml
hermes:
  version: "2.0.0"
  name: "sec-rss-skills-agent"
  description: "安全 RSS 日报 Hermes Agent"
  log_level: INFO
  log_file: "logs/hermes_agent.log"

llm_engine:
  default_provider: openai
  providers:
    openai:
      endpoint_env: AI_ENDPOINT
      api_key_env: AI_API_KEY
      model_env: AI_MODEL
      default_endpoint: "https://api.openai.com/v1/chat/completions"
      default_model: "gpt-4o-mini"
      timeout: 30
      max_retries: 3
      retry_delay: 1
    anthropic:
      endpoint_env: ANTHROPIC_ENDPOINT
      api_key_env: ANTHROPIC_API_KEY
      model_env: ANTHROPIC_MODEL
      default_model: "claude-3-sonnet-20240229"
      timeout: 30

skill_registry:
  auto_discover: true
  skill_paths:
    - skills/core
    - skills/pipelines
  hot_reload: false

context_manager:
  max_history_size: 100
  enable_persistence: true
  persistence_path: "data/context_history.json"

event_bus:
  enabled: true
  handlers:
    - type: logger
      config:
        log_file: "logs/skill_events.log"
    - type: metrics_collector
      config:
        metrics_file: "data/metrics.json"

cache:
  enabled: true
  backend: "memory"  # memory, redis, disk
  ttl: 3600
  max_size: 1000
```

---

### 7.2 skills/pipelines/sec_rss_daily/skill_config.yaml

```yaml
name: sec_rss_daily_pipeline
version: "2.0.0"
description: "完整安全 RSS 日报流水线"

# 依赖的原子技能
dependencies:
  - rss_fetch
  - deduplication
  - historical_penalty
  - fulltext_fetch
  - heuristic_scoring
  - ai_enrichment
  - cve_aggregation
  - semantic_cluster
  - markdown_render
  - archive_manager

# 流水线配置
pipeline:
  steps:
    - skill: rss_fetch
      config:
        opml_url: "https://github.com/zer0yu/CyberSecurityRSS/blob/master/tiny.opml"
        max_feeds: 120
        max_entries_per_feed: 15

    - skill: deduplication
      config:
        since_hours: 24

    - skill: historical_penalty
      config:
        archive_path: "data/seen_items.json"
        seen_penalty: 5

    - skill: fulltext_fetch
      enabled: false  # 可选步骤
      config:
        timeout_seconds: 8

    - skill: heuristic_scoring
      config: {}

    - skill: ai_enrichment
      config:
        max_items: 80
        timeout_seconds: 30
        categories:
          - 漏洞通告
          - 威胁情报
          - 攻击事件
          - 安全研究
          - 工具与产品
          - 政策与合规
          - 其他

    - skill: cve_aggregation
      config: {}

    - skill: semantic_cluster
      config:
        eps: 0.75
        min_samples: 1

    - skill: markdown_render
      config: {}

    - skill: archive_manager
      config:
        archive_path: "data/seen_items.json"
        output_dir: "output"
        report_name_format: "sec-daily-{date}.md"

# 执行策略
execution:
  retry_on_failure: false
  fail_fast: false  # 单个技能失败不中断流水线
  parallel: false   # 顺序执行
  timeout: 600      # 流水线总超时（秒）

# 监控和日志
monitoring:
  log_execution_time: true
  collect_metrics: true
  emit_events: true
```

---

### 7.3 skills/core/rss_fetch/skill_config.yaml

```yaml
name: rss_fetch
version: "2.0.0"
description: "从 RSS/OPML 源抓取新闻条目"

# 技能参数 schema
parameters:
  opml_url:
    type: string
    required: true
    description: "OPML 源文件 URL"
    default: "https://github.com/zer0yu/CyberSecurityRSS/blob/master/tiny.opml"

  max_feeds:
    type: integer
    required: false
    description: "最大抓取源数量"
    default: 120
    min: 1
    max: 500

  max_entries_per_feed:
    type: integer
    required: false
    description: "每个源最大抓取条目数"
    default: 15
    min: 1
    max: 100

  timeout_seconds:
    type: integer
    required: false
    description: "HTTP 请求超时时间"
    default: 10
    min: 1
    max: 60

# 输入要求
inputs:
  required: []  # 无前置依赖
  optional: []

# 输出声明
outputs:
  raw_items:
    type: "List[NewsItem]"
    description: "抓取的原始新闻条目列表"

# 依赖库
dependencies:
  python:
    - feedparser>=6.0.11
    - requests>=2.32.3
    - beautifulsoup4>=4.12.3

# 性能指标
performance:
  typical_execution_time: 20  # 秒
  max_memory_usage: 100       # MB
  cacheable: false
  idempotent: false

# 错误处理
error_handling:
  retry_on_failure: true
  max_retries: 3
  backoff_strategy: exponential
  fallback_skill: null
```

---

## 8. Hermes-Agent 主入口示例

### 8.1 hermes_agent.py

```python
#!/usr/bin/env python3
"""
Hermes-Agent 主入口
基于 Hermes-Agent 框架的安全 RSS 日报 Agent
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from hermes.core.skill_registry import SkillRegistry
from hermes.core.skill_router import SkillRouter
from hermes.core.skill_interface import SkillContext
from hermes.llm.reasoning_engine import LLMReasoningEngine
from hermes.config.config_manager import ConfigManager
from hermes.utils.logger import setup_logger

def main():
    parser = argparse.ArgumentParser(
        description="Hermes-Agent: 安全 RSS 日报 Agent"
    )
    parser.add_argument(
        "--config",
        default="hermes_config.yaml",
        help="Hermes 配置文件路径"
    )
    parser.add_argument(
        "--date",
        help="报告日期 (YYYY-MM-DD), 默认今天"
    )
    parser.add_argument(
        "--pipeline",
        default="sec_rss_daily_pipeline",
        help="执行的流水线技能名称"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="交互式模式"
    )
    args = parser.parse_args()

    # 1. 加载配置
    config_manager = ConfigManager(args.config)
    config = config_manager.load()

    # 2. 设置日志
    logger = setup_logger(
        log_level=config["hermes"]["log_level"],
        log_file=config["hermes"].get("log_file")
    )
    logger.info(f"Hermes-Agent v{config['hermes']['version']} 启动")

    # 3. 初始化 LLM 引擎
    llm_engine = LLMReasoningEngine(config["llm_engine"])
    logger.info(f"LLM 引擎初始化完成: {llm_engine.provider}")

    # 4. 初始化技能注册表
    skill_registry = SkillRegistry(
        config=config["skill_registry"],
        llm_engine=llm_engine,
        logger=logger
    )
    skill_registry.discover_and_register()
    logger.info(f"已注册 {len(skill_registry.skills)} 个技能")

    # 5. 初始化技能路由器
    skill_router = SkillRouter(skill_registry, logger=logger)

    # 6. 交互式模式或单次执行
    if args.interactive:
        interactive_mode(skill_router, config)
    else:
        execute_pipeline(
            skill_router=skill_router,
            pipeline_name=args.pipeline,
            date=args.date,
            config=config,
            logger=logger
        )

def interactive_mode(skill_router, config):
    """交互式 Agent 模式"""
    print("=" * 60)
    print("Hermes-Agent 交互式模式")
    print("输入自然语言指令，Agent 将自动选择合适的技能执行")
    print("输入 'exit' 或 'quit' 退出")
    print("=" * 60)

    while True:
        try:
            query = input("\n> ").strip()
            if query.lower() in ["exit", "quit"]:
                print("再见！")
                break

            if not query:
                continue

            # 技能路由和执行
            context = SkillContext(
                data={},
                metadata={"query": query, "timestamp": datetime.utcnow()},
                config=config,
                history=[]
            )

            result = skill_router.route_and_execute(query, context)

            if result.success:
                print(f"\n✅ 执行成功:")
                print(result.output)
            else:
                print(f"\n❌ 执行失败: {result.error}")

        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")

def execute_pipeline(skill_router, pipeline_name, date, config, logger):
    """执行指定流水线"""
    # 准备日期
    if date:
        report_date = datetime.strptime(date, "%Y-%m-%d").date()
    else:
        report_date = datetime.utcnow().date()

    logger.info(f"执行流水线: {pipeline_name}, 日期: {report_date}")

    # 构建上下文
    context = SkillContext(
        data={},
        metadata={
            "date": report_date.strftime("%Y-%m-%d"),
            "timestamp": datetime.utcnow()
        },
        config=config,
        history=[]
    )

    # 获取流水线技能
    try:
        pipeline_skill = skill_router.registry.get(pipeline_name)
        if not pipeline_skill:
            logger.error(f"流水线技能未找到: {pipeline_name}")
            sys.exit(1)

        # 执行流水线
        logger.info(f"开始执行流水线...")
        result = pipeline_skill.execute(context)

        if result.success:
            logger.info(f"✅ 流水线执行成功")
            logger.info(f"报告输出: {result.output.get('report', 'N/A')}")
            print(f"\n✅ 安全日报生成成功!")
            print(f"报告路径: {result.output.get('report', 'N/A')}")
        else:
            logger.error(f"❌ 流水线执行失败: {result.error}")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"流水线执行异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## 9. 向后兼容性 (Backward Compatibility)

为保持与 v1.0 的兼容性，提供兼容层:

### 9.1 保留 run.sh 入口
```bash
#!/usr/bin/env bash
# skills/sec-rss-daily/run.sh
# v2.0 兼容层：调用 Hermes-Agent

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"

# 调用 Hermes-Agent 执行流水线
python3 hermes_agent.py \
    --config hermes_config.yaml \
    --pipeline sec_rss_daily_pipeline \
    --date "${1:-}"
```

### 9.2 保持 SKILL.md 兼容性
- 保留 agentskills.io 规范的必需字段
- 添加 Hermes-Agent 特定元数据
- 在 `metadata.agents` 中声明 `hermes-agent` 支持

---

## 10. 迁移检查清单 (Migration Checklist)

### 10.1 功能对等性验证
- [ ] RSS 抓取功能完整迁移
- [ ] 去重和时间过滤逻辑一致
- [ ] 历史惩罚机制保持
- [ ] AI 增强功能正常
- [ ] 启发式评分规则对齐
- [ ] CVE 聚合逻辑一致
- [ ] 语义聚类结果对齐
- [ ] Markdown 输出格式保持

### 10.2 性能验证
- [ ] 端到端执行时间 ≤ v1.0 + 10%
- [ ] 内存使用 ≤ v1.0 + 20%
- [ ] 并发抓取性能对比
- [ ] LLM 调用优化（批处理）

### 10.3 测试覆盖率
- [ ] 所有原子技能单元测试 ≥ 90%
- [ ] 流水线集成测试覆盖主要场景
- [ ] E2E 测试验证完整流程
- [ ] 错误处理和降级测试

### 10.4 文档完整性
- [ ] 更新 README.md
- [ ] 编写技能开发指南
- [ ] 编写 v1→v2 迁移指南
- [ ] 更新 SKILL.md
- [ ] 添加 API 文档
- [ ] 添加配置示例

---

## 11. 风险评估与缓解 (Risk Assessment)

### 11.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 重构引入新 Bug | 高 | 中 | 全面测试覆盖；保留 v1 作为备份；分阶段发布 |
| 性能下降 | 中 | 低 | 性能基准测试；优化关键路径；批量处理 |
| 技能依赖冲突 | 中 | 低 | 依赖声明和验证；隔离技能环境 |
| LLM 调用成本增加 | 中 | 低 | 批量调用优化；缓存策略；请求限流 |

### 11.2 兼容性风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 破坏 v1 兼容性 | 高 | 低 | 提供兼容层；保留 run.sh 入口；版本共存 |
| agentskills.io 规范不兼容 | 中 | 低 | 遵循规范；保持 SKILL.md 标准格式 |
| 配置迁移困难 | 中 | 中 | 提供配置转换工具；详细迁移文档 |

### 11.3 项目风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 开发周期超期 | 中 | 中 | 分阶段交付；MVP 优先；增量迭代 |
| 团队学习曲线 | 低 | 中 | 详细文档；代码示例；开发指南 |
| 社区采用率低 | 中 | 低 | 保持简单易用；提供迁移工具；示例项目 |

---

## 12. 成功指标 (Success Metrics)

### 12.1 技术指标
- ✅ 所有 v1 功能完整迁移
- ✅ 测试覆盖率 ≥ 90%
- ✅ 端到端执行时间 ≤ v1 + 10%
- ✅ 代码模块化程度 > 80% (10+ 独立技能)
- ✅ 技能可重用性 > 50% (技能被多个流水线使用)

### 12.2 可用性指标
- ✅ 技能开发时间减少 50% (模板化)
- ✅ 新流水线创建时间 < 30 分钟
- ✅ 配置迁移成功率 100%
- ✅ 文档完整性 100%

### 12.3 扩展性指标
- ✅ 新增 ≥ 3 个新技能（快速扫描、CVE 监控、实时告警）
- ✅ 支持 ≥ 2 个 LLM 提供商（OpenAI + Anthropic）
- ✅ 技能热插拔支持
- ✅ 社区贡献技能机制

---

## 13. 下一步行动 (Next Steps)

### 13.1 立即行动（本周）
1. ✅ **已完成**: 创建本设计文档
2. **待办**: 获取团队和社区反馈
3. **待办**: 确定技术栈和依赖
4. **待办**: 创建项目分支 `feature/hermes-agent-v2`

### 13.2 短期计划（本月）
1. 实施阶段 1：基础设施（Week 1-2）
2. 实施阶段 2：核心技能迁移（Week 3-4）
3. 每周进度审查和调整

### 13.3 长期愿景（下季度）
1. 发布 v2.0.0 正式版
2. 构建技能市场和社区
3. 支持更多 AI Agent 框架
4. 企业级特性（权限、审计、SLA）

---

## 14. 总结 (Conclusion)

本重构设计将 sec-rss-skills 从单体脚本架构升级为基于 Hermes-Agent 的模块化技能框架，带来以下核心价值:

1. **模块化**: 10 个独立原子技能，可单独测试和重用
2. **可扩展性**: 轻松添加新技能和流水线
3. **灵活性**: 动态技能编排和策略选择
4. **标准化**: 遵循 Hermes-Agent 和 agentskills.io 规范
5. **可维护性**: 清晰的职责分离和依赖管理

通过 8 周的分阶段实施，我们将在保持向后兼容的同时，为项目带来长期的技术红利和社区生态。

---

**版本历史**:
- v1.0 (2024): 初始版本，基于 agentskills.io 规范
- v2.0 (2026-05-03): Hermes-Agent 重构设计方案

**维护者**: gwokfun
**许可证**: MIT
**仓库**: https://github.com/gwokfun/sec-rss-skills
