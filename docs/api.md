# API 参考

## 通用约定

- 基础路径：`/api`
- 认证：登录后由服务端 session cookie 维持；未登录返回 `401`，权限不足返回 `403`
- 请求体：所有 `POST` / `PATCH` / `DELETE` 请求**必须**携带 JSON body（即使无参数也需传 `{}`）
- 响应：`Content-Type: application/json`，且 `Cache-Control: no-store`
- 错误格式：`{"message": "...", "field": "..."}`（`field` 仅在字段校验失败时出现）
- 时间：日期 `YYYY-MM-DD`，时间 `HH:MM`（30 分钟粒度）；预约时长 0.5–8 小时

## 认证与账号

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/api/auth/login` | 公开 | 登录；参数 `username`、`password` |
| POST | `/api/auth/logout` | 登录用户 | 登出 |
| PATCH | `/api/auth/profile` | 登录用户 | 更新 `phone`、`email` |
| PATCH | `/api/auth/password` | 登录用户 | 改密；参数 `current`、`password`、`confirm` |
| PATCH | `/api/admin/users/<username>` | admin | 管理账号；参数 `role`、`enabled`、可选 `password` |

## 工作台与场地

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/workspace` | 登录用户 | 工作台聚合数据（按角色返回） |
| GET | `/api/venues` | 登录用户 | 场地列表，支持分页与 `q`/`building`/`type`/`status`/`min_capacity`/`max_capacity` 过滤 |
| GET | `/api/venues/<venue_id>` | 登录用户 | 场地详情 |
| GET | `/api/venues/<venue_id>/schedule` | 登录用户 | 场地排期；参数 `?date=YYYY-MM-DD` |
| POST | `/api/venues` | manager | 新增场地 |
| PATCH | `/api/venues/<venue_id>` | manager | 编辑场地 |
| POST | `/api/venue-locks` | manager | 锁定场地时段；参数 `venue`、`date`、`start`、`end`、`reason` |
| DELETE | `/api/venue-locks/<lock_id>` | manager | 解除锁定 |

## 物资

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/equipments` | 登录用户 | 物资列表；传 `date`/`start`/`end` 时返回该时段 `available` |
| POST | `/api/equipments` | manager | 新增物资 |
| PATCH | `/api/equipments/<equipment_id>` | manager | 编辑物资 |

## 预约与审批

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/reservations/my` | student | 我的申请 |
| POST | `/api/reservations` | student | 创建预约/草稿；`draft: true` 表示存草稿 |
| GET | `/api/reservations/<id>` | 登录用户 | 预约详情 |
| PATCH | `/api/reservations/<id>` | student | 编辑（仅草稿/已驳回） |
| DELETE | `/api/reservations/<id>` | student | 删除草稿 |
| POST | `/api/reservations/<id>/cancel` | student/manager/admin | 取消预约 |
| PATCH | `/api/reservations/<id>/schedule` | manager | 调整排期；参数 `venue`、`date`、`start`、`end`、`comment` |
| GET | `/api/approvals/pending` | advisor/manager | 待办审批列表；参数 `?sort=date` |
| POST | `/api/approvals/<id>/audit` | advisor/manager | 审批；参数 `decision`（`APPROVED`/`REJECTED`）、`comment` |

## 管理

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/admin/audit` | admin | 审计日志 |
| POST | `/api/admin/reset-demo` | admin | 恢复演示数据并重置 session |

## 角色与状态

- 角色 `Role`：`student` / `advisor` / `manager` / `admin`
- 预约状态 `Status`：`DRAFT → PENDING_ADVISOR → PENDING_VENUE → APPROVED`；终态 `REJECTED` / `CANCELLED` / `FINISHED`
- 审批路由：指导教师审批 `PENDING_ADVISOR`（仅本学院），场地管理员审批 `PENDING_VENUE`
