# 贡献指南

感谢你对 CampusVenueScheduler 的关注！本指南帮助你以最低摩擦提交被接受的变更。

> 完整的开发历程规范（分支模型、版本策略、发布闭环）见 [docs/development-workflow.md](docs/development-workflow.md)。

## 提交规范（Conventional Commits）

提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/)，格式：

```
<type>(<scope>): <subject>
```

常见 `type`：

| type | 用途 |
|---|---|
| `feat` | 新功能 |
| `fix` | 修复 bug |
| `docs` | 仅文档变更 |
| `refactor` | 重构（不改行为） |
| `test` | 新增/修改测试 |
| `chore` | 构建/工具等杂项 |

**正例**：`feat(booking): 支持预约改期`
**反例**：`update code`、`fix stuff`、`wip`

## 开发流程

1. **Fork 并新建分支**：本项目采用 trunk-based，从 `main` 拉出短命分支 `feat/xxx`、`fix/xxx`。
2. **修改**：保持改动聚焦单一目的。
3. **跑测试**：`python -m pytest --cov=app`（覆盖率目标 ≥ 80%）。
4. **跑 lint**：`ruff check .`。
5. **提交**：使用 Conventional Commits 信息。
6. **发起 PR**：按 [PR 模板](.github/PULL_REQUEST_TEMPLATE.md) 填写，说明动机与改动。

## 代码风格

- **Python**：遵循 `ruff`（配置见 `pyproject.toml`），4 空格缩进，双引号。
- **类型标注**：函数签名需有类型标注（签名级即可，不强求 strict mypy）。
- **错误处理**：业务错误统一抛 `ApiError(message, status, field=...)`，勿吞异常。
- **数据库访问**：写操作经 `database.transaction(db)`，读操作勿带副作用（`finish_expired` 除外，已文档化）。
- **前端文案与 API 消息**：保持中文一致。

## 测试约定

- 单元测试：`tests/test_*.py` 中直接注入临时 `db` 断言纯逻辑。
- 集成测试：用 `app.test_client()` 走完整 HTTP 流程，按角色 fixture 登录。
- 新增行为应配套测试；修复 bug 应先写复现用例。

不确定之处，欢迎先开 Issue 讨论再动手。
