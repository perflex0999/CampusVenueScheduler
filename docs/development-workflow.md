# 开发历程规范

本文档是维护者与贡献者的开发流程总规范，涵盖分支模型、提交规范、版本策略与发布闭环。贡献者快速版见 [CONTRIBUTING.md](../CONTRIBUTING.md)。

## 1. 分支模型：trunk-based（主干开发）

**决策**：采用 trunk-based，单一主干 + 短命功能分支。

**取舍理由**：

- 本项目为单人 / 小团队、功能边界清晰、需求稳定。trunk-based 分支少、合并少、CI 只需维护一条主线，认知负担最低。
- Git Flow 的 `develop / feature / release / hotfix` 多分支，适合「多版本并行维护 + 固定发布窗口」的团队；对本项目是过度设计。
- 代价是缺少 release 分支的「发布冻结」能力；对本项目规模，直接打 tag 即可满足，无需专门分支。

**约定**：

- 主干 `main` 始终保持可运行、可发布。
- 功能 / 修复用短命分支 `feat/xxx`、`fix/xxx`，完成后合并回 `main` 并删除分支。
- 单人开发可在 `main` 直接提交小改动，但破坏性或实验性改动一律用分支。

## 2. Commit 规范（Conventional Commits）

格式：`<type>(<scope>): <subject>`，subject 用祈使句、中文或英文均可，控制在 ~72 字符内。

| type | 用途 |
|---|---|
| `feat` | 新功能 |
| `fix` | 修复 bug |
| `docs` | 仅文档变更 |
| `refactor` | 重构（不改行为） |
| `test` | 新增 / 修改测试 |
| `chore` | 构建、工具、依赖等杂项 |

**正例**：

```text
feat(booking): 支持预约改期
fix(auth): 修复连续登录失败计数错误
test(booking): 补充半开区间冲突检测边界用例
docs(api): 补充取消预约接口说明
```

**反例**：

```text
update code        # 缺 type，语义不清
fix stuff          # subject 空泛，说不出改了什么
wip                # 未完成状态的占位提交
改了点东西          # 未遵循 type(scope): subject 结构
```

## 3. 版本策略（SemVer）

版本号 `MAJOR.MINOR.PATCH`（如 `1.2.3`）：

- **MAJOR**：破坏性 API 变更
- **MINOR**：向后兼容的新功能
- **PATCH**：向后兼容的 bug 修复

**预发布链**：`1.1.0-alpha.1 → 1.1.0-beta.1 → 1.1.0-rc.1 → 1.1.0`

**发布节奏**：无固定周期，按功能完成度发布；PATCH 可随时发，MINOR 按功能集发布，MAJOR 需谨慎并给出迁移说明。

## 4. CHANGELOG 与 Release Notes

| | `CHANGELOG.md` | Release Notes |
|---|---|---|
| 读者 | 用户 + 开发者 | 最终用户 |
| 粒度 | 按版本全量变更清单 | 单次发布的亮点摘要 |
| 格式 | Keep a Changelog（Added / Changed / Fixed / Removed） | 自由叙事 + 升级指引 |
| 维护时机 | 随代码提交持续更新 | 发布时写，放 GitHub Release |

原则：**CHANGELOG 记全，Release Notes 讲重点。** CHANGELOG 是长期累积的事实记录；Release Notes 是每次发布时面向用户的一次性摘要。

## 5. Issue → PR → Review → Merge → Release 闭环

1. **Issue**：bug 用 `bug_report` 模板，需求用 `feature_request` 模板，先讨论再动手。
2. **分支**：从 `main` 拉出 `feat/xxx` 或 `fix/xxx`。
3. **PR**：关联 Issue，按 PR 模板填写，跑通 `python -m pytest` 与 `python -m ruff check .`。
4. **Review**：维护者审阅 + CI 全绿（阶段 5 落地）后方可合并。
5. **Merge**：优先 squash（单提交、历史清晰）。
6. **Release**：更新 `CHANGELOG.md` → 打 tag `vX.Y.Z` → 写 Release Notes。

## 6. 里程碑与 Roadmap 维护

- **GitHub Milestones**：短期可交付批次（如「v1.1 排期增强」），关联 Issue，用于跟踪进度。
- **`ROADMAP.md`**：长期方向（时间宽松），按「近期 / 已完成」分区，完成即勾选。
- 二者关系：Roadmap 的「近期」条目拆成 Milestone 落地；Milestone 完成后再回填 Roadmap 的「已完成」。
