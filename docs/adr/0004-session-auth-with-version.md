# ADR-0004: 会话认证 + auth_version 失效机制

- 状态：已接受
- 日期：2026-11-23

## 决策背景

需要为四类角色提供登录态，并在「改密 / 改角色 / 停用账号」后**立即**使旧会话失效。可在「Flask 服务端 session」与「JWT 无状态令牌」之间选择。

## 决策

采用 **Flask 服务端 session**，并在 `users.auth_version` 上做失效控制：

- `session` 存 `uid` + `version`；`current_user()` 每次请求重读 `users` 行并比对 `auth_version`。
- 任何改密 / 改角色 / 停用操作都会 `token_urlsafe()` 重生成 `auth_version`，从而让所有旧会话在下次请求被判定失效（`session.clear()` 后返回 401）。
- `secret_key` 持久化在 `settings` 表，重启不丢登录态；登录失败 5 次锁定 5 分钟（`login_attempts` 表）。

## 备选方案

- **JWT**：无状态但「改密后旧令牌仍有效」是经典难点，需要黑名单或短过期，复杂度反超服务端 session；本系统单机部署，无水平扩展诉求，否决。
- **纯 session 无版本号**：无法即时踢人，需等 session 自然过期，否决。

## 后果

- 正面：改密/改角色/停用即时生效，实现简单且可测试。
- 负面：每次请求多一次 `users` 查询（单机 SQLite 下开销可忽略）；水平扩展时需共享 session 存储（当前无此需求）。
