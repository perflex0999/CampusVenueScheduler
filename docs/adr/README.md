# 架构决策记录（ADR）

本目录记录本项目「非显而易见」的技术决策。每条 ADR 遵循固定结构（状态 / 日期 / 背景 / 决策 / 备选 / 后果），便于后续维护者理解「为什么当初这样做」。

| 编号 | 标题 | 状态 |
|---|---|---|
| [0001](0001-flask-not-fastapi.md) | 选择 Flask 而非 FastAPI | 已接受 |
| [0002](0002-raw-sql-not-orm.md) | 采用裸 SQL 而非 ORM | 已接受 |
| [0003](0003-vanilla-js-no-build.md) | 原生 JS 单页应用、无构建工具 | 已接受 |
| [0004](0004-session-auth-with-version.md) | 会话认证 + auth_version 失效机制 | 已接受 |

新增 ADR 时：复制下方模板，编号递增，并把 README 表格补一行。
