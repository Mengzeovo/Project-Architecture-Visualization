# Project Architecture Visualization

`archviz` 是一个面向工程落地的架构分析工具：
给它一个项目目录，它会从代码和配置中提取结构化事实，生成可直接使用的
`D2 + SVG` 架构图。

这个项目的核心目标很明确：

- 实用优先（先解决真实项目中的理解问题）
- 证据可追溯（不是“猜出来”的架构）
- v1 保持简洁（不堆不必要的复杂机制）

---

## 1. 它解决什么问题

当仓库变大后，架构信息通常分散在代码、配置、约定和文档里，导致：

- 新人上手慢
- 跨团队沟通成本高
- 架构图和实际代码长期不一致

`archviz` 通过自动提取来回答几个关键问题：

- 当前项目有哪些容器/服务？
- 模块之间如何依赖？
- 对外 API 从哪里暴露？
- 哪些模块在访问外部 HTTP/数据库/缓存/消息系统？

---

## 2. 它是怎么发挥作用的（核心流程）

`archviz` 采用确定性流水线：

1. **扫描（Scan）**：扫描项目文件与清单（manifest）
2. **容器发现（Discover）**：自动识别服务/容器边界（无需手动指定入口）
3. **事实提取（Extract）**：语言提取器 + 通用提取器提取关系
4. **图归一化（Normalize）**：统一写入 Graph IR（节点/边/证据/置信度）
5. **视图构建（View）**：生成容器视图、模块视图、功能视图
6. **渲染（Render）**：输出 D2，并在本机有 `d2` 时输出 SVG
7. **报告（Report）**：输出低置信度边和低置信功能归属，便于人工校验

这套分层的意义是：

- 抽取层负责“事实”
- 渲染层负责“展示”
- 后续 AI 只负责“解释”，不直接篡改事实层

---

## 3. 设计原则

- **证据优先**：关键节点/边尽量附带 `file + line + rule_id`
- **置信度分级**：推断关系低于静态可证关系
- **通用架构**：
  - TS/JS、Python 走深度提取
  - 其他生态先提供通用结构可视化
- **本地可运行**：偏离线、本地分析场景

---

## 4. 能力矩阵

### 4.1 深度提取（语义更强）

- TypeScript / JavaScript
  - `import/require` 依赖关系
  - Express 风格路由信号（如 `app.get(...)`）
  - HTTP/数据访问调用信号
- Python
  - AST import 关系
  - FastAPI 路由装饰器信号
  - HTTP/数据访问调用信号

### 4.2 通用提取（基础覆盖）

- C/C++、Go、Java/Kotlin、C#、Rust、PHP、Ruby
  - 可产出容器/模块结构图
  - 可结合 manifest 补充依赖语义

### 4.3 manifest/依赖信号

- JavaScript：`package.json`
- Python：`pyproject.toml`、`requirements*.txt`
- C/C++：`CMakeLists.txt`、`conanfile.*`、`meson.build`、`vcpkg.json`
- 其他：`go.mod`、`Cargo.toml`、`pom.xml`、`build.gradle*`、`composer.json`、`Gemfile`

---

## 5. 输出产物

默认输出目录为 `.archviz`，包含：

- `architecture.ir.json`：统一图模型（节点、边、置信度、证据）
- `feature.ir.json`：功能分组 IR（功能、模块归属、依赖、外部交互、证据）
- `feature-index.md`：功能总览入口
- `report.md`：摘要与低置信度关系清单
- `views/container-view.d2`
- `views/module-view.d2`
- `views/container-view.svg`（若系统安装了 `d2`）
- `views/module-view.svg`（若系统安装了 `d2`）
- `features/<feature-id>/diagram.d2`
- `features/<feature-id>/diagram.svg`（若系统安装了 `d2`）
- `features/<feature-id>/design.md`
- `features/<feature-id>/evidence.json`

---

## 6. 安装

环境要求：

- Python 3.11+
- 可选：`d2` CLI（用于导出 SVG）

安装：

```bash
pip install -e .
```

---

## 7. 使用方式

分析一个项目：

```bash
archviz /path/to/project
```

指定输出目录：

```bash
archviz /path/to/project --output /path/to/output
```

指定功能覆写配置：

```bash
archviz /path/to/project --feature-map /path/to/feature-map.yaml
```

本地模块方式运行：

```bash
PYTHONPATH=src py -3 -m archviz.cli /path/to/project
```

---

## 8. 为什么这个方案实用

架构可视化常见两类问题：

- 纯手工建模：维护成本高，容易过时
- 纯 LLM 推理：可读性高但事实不稳定

`archviz` 采用中间路线：

- 用确定性规则/语法信息构建事实层
- 用置信度表达不确定性
- 用 D2/SVG 提供可直接消费的结果
- 用 IR 支撑后续自动化扩展

---

## 9. 当前限制

- 目前深度语义提取仍以 TS/JS、Python 为主。
- 动态反射、运行时拼装 import、宏展开等场景无法完全静态还原。
- 通用语言支持当前更偏结构可视化，细粒度语义仍可继续增强。

---

## 10. 推荐后续路线

1. 增加 C/C++ 深度提取器（`#include`、target 依赖、入口 `main`、CMake target 图）
2. 增加 `--min-confidence` 过滤参数，默认图更干净
3. 完善插件接口，按语言渐进增强
4. 增加 golden IR 快照测试，保障规则演进稳定性

---

## 11. 项目结构

- `src/archviz/scanner.py`：项目扫描
- `src/archviz/containers.py`：容器/服务根自动发现
- `src/archviz/extractors/`：提取器集合
- `src/archviz/models.py`：Graph IR 与构图器
- `src/archviz/transforms.py`：图增强与统计
- `src/archviz/views.py`：视图构建
- `src/archviz/features/`：Feature IR、分类、功能视图与文档输出
- `src/archviz/renderers/d2.py`：D2/SVG 渲染
- `src/archviz/report.py`：分析报告输出
- `src/archviz/cli.py`：CLI 入口

---

## 12. 一句话总结

`archviz` 可以把“一个项目目录”转成“可追溯、可落地的架构图和图模型”，
帮助团队更快理解和维护系统架构。
