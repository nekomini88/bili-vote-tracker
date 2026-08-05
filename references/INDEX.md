# Reference Index

> 本索引是 `dev-requirements-flow` 规范的入口。
> 定义各专项规范（References）的用途、适用场景和加载规则。

---

## Capability Matrix（能力矩阵）

并非所有项目都需要全部规范。
AI 必须根据项目类型自动选择需要加载的 References。

| Project Type | 推荐 References | 说明 |
|-------------|----------------|------|
| python_cli | testing + release | Python 命令行工具 |
| web_fullstack | architecture + ui + devops + testing + security | 前后端 Web 应用 |
| ai_agent | architecture + prompt + testing + security | AI Agent / LLM 应用 |
| docker_service | devops + security + docker | 容器化服务 |
| library_sdk | api + release + testing | 库 / SDK |
| frontend | ui + testing + devops | 纯前端项目 |
| backend | architecture + devops + security + testing | 后端服务 |
| migration | architecture + risk | 系统迁移/升级 |

---

## Reference Catalog

| 文件 | 状态 | 职责 |
|------|------|------|
| `INDEX.md` | Stable | 本文件，规范索引与 Capability Matrix |
| `architecture.md` | Stable | 架构规范：ADR、模块划分、接口设计、层次边界 |
| `ui.md` | Draft | UI/UX 规范：Design System、组件库、响应式、可访问性 |
| `testing.md` | Stable | 测试规范：单元测试、集成测试、覆盖率、测试数据 |
| `devops.md` | Stable | DevOps 规范：CI/CD、部署、回滚、监控、告警 |
| `security.md` | Stable | 安全规范：输入校验、输出过滤、权限控制、依赖审计 |
| `docker.md` | Draft | Docker 规范：多阶段构建、镜像优化、Compose 规范 |
| `git.md` | Stable | Git 规范：Commit Convention、Branch 策略、PR 流程 |
| `release.md` | Stable | 发布规范：版本号、Release Note、Git Tag、回滚策略 |
| `prompt.md` | Draft | Prompt 规范：提示词模板、上下文管理、输出约束 |

---

## Loading Policy（加载策略）

AI 辅助开发时，按以下规则加载 References：

1. **默认加载**：仅加载 Core Rules + Workflow + Engineering（已内置在 `dev-requirements-flow` Skill 中）。
2. **项目类型匹配**：读取 Project Manifest（若存在）中的 `project.type`，按 Capability Matrix 加载对应 References。
3. **显式要求**：若用户明确要求某项规范，无论项目类型如何，都必须加载。
4. **最小加载**：未被加载的 Reference 不得影响当前任务判断。

---

## How to Use

当用户发起开发任务时，AI 应当：

1. 判断项目类型（python_cli / web_fullstack / ai_agent / docker_service / library_sdk / frontend / backend / migration）
2. 检查项目根目录是否存在 `spec.yaml`（Project Manifest）
3. 若存在 Manifest，读取 `references` 列表，按列表加载
4. 若不存在 Manifest，按 Capability Matrix 推荐列表加载
5. 若仍不确定，向用户询问项目类型

---

## Contributing

新增 Reference 时，必须遵循以下模板：

```
# <Reference Name> Specification

## Version
- Spec Version: x.y.z

## Scope
- 适用于：...

## Normative Keywords
- MUST / SHOULD / MAY / MUST NOT

## Rules
...

## Examples
...
```

所有新增 Reference 必须更新本索引。
