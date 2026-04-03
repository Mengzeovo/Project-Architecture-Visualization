# 功能分组架构图与设计说明技术方案

## 1. 背景与目标

当前系统已经可以生成“代码联系图”（模块依赖、容器归属、部分路由和外部依赖信号），但对于大型仓库仍有两个核心痛点：

1. 单图过大，可读性差。
2. 难以回答“某个功能是怎么设计的、代码在哪里”。

本方案目标是将现有能力升级为：

- **按功能（Feature）分类的架构图**
- **每个功能一份可追溯的设计说明文件**

最终输出应面向工程实践，重点满足“刚接触项目的人可以快速上手”：

- 快速理解项目的**目标**（项目要解决什么问题）
- 快速理解项目的**功能**（有哪些业务能力、各自边界是什么）
- 快速理解项目的**架构**（模块和服务如何协作）
- 快速找到继续深入的**切入点**（入口文件、核心模块、关键链路）

并兼顾代码审查、架构沟通和变更评估。


## 2. 设计原则

- **实用优先**：先产出可用结果，再逐步提高语义深度。
- **事实优先**：结构事实来自静态提取，不依赖模型“猜测”。
- **可追溯**：每个关键结论可回溯到文件和行号。
- **分层输出**：全局图 + 功能图 + 说明文档，避免单一大图。
- **可覆盖**：支持人工覆写分类规则（feature-map）。


## 3. 技术选型与职责

### 3.1 必选技术

1. `Tree-sitter`
   - 职责：多语言语法树解析，提取 import/call/route/include 等结构事实。
   - 价值：保证跨语言扩展能力和提取稳定性。

2. `Graph IR`（项目内自定义）
   - 职责：统一承载节点、边、证据、置信度。
   - 价值：解耦“提取层”和“渲染层”，便于迭代。

3. `D2`
   - 职责：将图模型输出为 `.d2` + `.svg`。
   - 价值：架构表达能力强，适合复杂图。

4. 规则引擎（目录规则 + 命名规则 + 入口扩散）
   - 职责：将模块归属到 Feature，构建“功能视图”。
   - 价值：实现“按功能分类”的核心能力。

### 3.2 推荐增强

1. `MkDocs`
   - 职责：组织功能说明文档站点。
   - 价值：便于团队浏览和持续维护。

2. `feature-map.yaml`
   - 职责：人工覆写自动分类结果。
   - 价值：解决边界模糊和命名不一致问题。

3. `networkx`
   - 职责：做图聚合、路径分析、社区发现、降噪。
   - 价值：把“代码联系图”提升为“架构视图”。

### 3.3 后续可选

1. `OpenTelemetry`
   - 职责：引入运行时链路，叠加动态视图。
   - 价值：从静态关系图升级到真实请求路径图。


## 4. 目标产物

执行 `archviz` 后，新增以下功能级产物：

```text
.archviz/
  architecture.ir.json
  feature-index.md
  features/
    <feature-id>/
      diagram.d2
      diagram.svg
      design.md
      evidence.json
```

其中：

- `feature-index.md`：功能清单与依赖关系入口。
- `diagram.*`：该功能的架构图。
- `design.md`：该功能的设计说明。
- `evidence.json`：该功能结论的证据集合。


## 5. 核心模型设计

### 5.1 Feature IR（新增）

说明：`IR` 是 `Intermediate Representation` 的缩写，中文通常叫“中间表示”或“中间模型”。
在本方案中，Feature IR 指“功能层的标准化数据结构”，用于连接提取、分析、渲染和文档输出。

在现有 Graph IR 之上增加功能层抽象：

- `feature_id`: 功能唯一标识
- `name`: 功能名
- `entrypoints`: 入口点（路由、命令、任务等）
- `modules`: 归属模块列表
- `dependencies`: 依赖的其他 feature/shared/infra
- `external_interactions`: 外部系统交互（HTTP/DB/MQ）
- `evidence_refs`: 证据列表（file/line/rule_id）
- `confidence`: 功能分类置信度

### 5.2 feature-map 覆写配置

新增配置文件 `.archviz/feature-map.yaml`（或仓库根目录 `feature-map.yaml`）：

```yaml
features:
  auth:
    include:
      - "services/auth/**"
      - "commands/login/**"
    exclude:
      - "**/*.test.ts"
  billing:
    include:
      - "services/billing/**"

shared:
  - "utils/**"
  - "types/**"

infra:
  - "services/api/**"
  - "services/mcp/**"
```


## 6. 分类与建图算法

### Step A: 候选功能发现

- 目录启发：`commands/*`, `services/*`, `features/*`, `modules/*`
- 入口启发：路由、CLI command、任务入口
- 命名启发：文件名/目录名关键词（auth/payment/search...）

可选增强（建议在大型仓库开启）：

- 引入 LLM 做“候选功能补全与重命名建议”，例如把零散目录归并为更稳定的功能名。
- LLM 仅用于“建议候选集合”，不直接写入最终结果；最终归属仍由规则和证据校验通过后落库。
- 对每个 LLM 建议输出 `reason + evidence_refs + confidence`，便于人工审核和回溯。

### Step B: 模块归属判定

按优先级判定：

1. `feature-map` 显式规则
2. 入口反向扩散（entrypoint -> imported modules）
3. 路径/命名规则
4. 图聚类兜底（低置信度）

### Step C: 功能依赖计算

- 将模块边投影为 feature 边
- 过滤测试、脚本、生成文件噪声
- 保留跨功能关键边（imports/http/reads/writes/publishes）

### Step D: 解释文档生成

每个 feature 自动生成 `design.md`，包含：

1. 功能目标
2. 入口点
3. 核心模块与职责
4. 对外依赖与外部交互
5. 关键链路示例
6. 证据引用


## 7. 文档模板（design.md）

```md
# Feature: <name>

## 功能目标
- ...

## 入口点
- `path/to/file.ts:line` - command/route/handler

## 核心模块
- `moduleA`：...
- `moduleB`：...

## 依赖关系
- 依赖 Feature: ...
- 依赖 Shared: ...
- 外部系统: ...

## 关键链路
- `entry -> service -> repository -> external`

## 证据
- `src/...:123` (rule_id: ...)
```


## 8. 与现有系统的集成点

基于当前代码，建议新增模块：

- `src/archviz/features/models.py`：Feature IR 数据模型
- `src/archviz/features/classifier.py`：功能分类与归属
- `src/archviz/features/views.py`：功能级视图构建
- `src/archviz/features/docs.py`：`design.md` 与 `feature-index.md` 生成
- `src/archviz/features/config.py`：`feature-map.yaml` 读取与校验

并在 `src/archviz/pipeline.py` 中增加 Feature 阶段。


## 9. 分阶段实施计划

### Phase 1（MVP，1-2 周）

- Feature IR 定义
- 自动功能发现（目录+入口+命名）
- 输出 `feature-index.md` + 每功能 `diagram.d2`
- 每功能 `design.md` 基础模板生成

验收标准：

- 在大型 TS 仓库中可稳定产出 5+ 功能分图
- 每个功能说明至少包含入口、核心模块、依赖、证据

### Phase 2（增强，1-2 周）

- 支持 `feature-map.yaml` 覆写
- 增加低置信分类提示与人工修正建议
- 输出 `evidence.json`

验收标准：

- 分类可人工纠偏，误分配可控
- 功能文档可直接用于评审

### Phase 3（进阶）

- 支持动态链路叠加（OpenTelemetry）
- 生成“静态结构 + 动态流量”联合视图


## 10. 风险与应对

1. 功能边界歧义
   - 应对：引入 `feature-map` 覆写 + 置信度标签。

2. 大仓库渲染超时
   - 应对：按功能拆图，限制单图节点规模。

3. 动态行为难静态还原
   - 应对：低置信提示 + 后续引入 trace 数据。


## 11. 成功标准（Definition of Done）

- 能自动产出“全局功能图 + 每功能分图 + 每功能说明文档”。
- 文档中的关键结论可回溯到代码证据。
- 大仓库场景下可在可接受时间内完成（支持分批渲染）。
- 架构评审可直接基于输出结果进行讨论，而非人工补图。


## 12. 一句话方案总结

以现有静态代码联系图为事实基础，引入 Feature 分层、规则分类和文档生成，构建“按功能组织的架构图 + 功能设计说明”体系，并保留后续叠加运行时链路的扩展能力。
