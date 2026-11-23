# ADR-0002: 采用裸 SQL 而非 ORM

- 状态：已接受
- 日期：2026-11-23

## 决策背景

数据层需要访问 SQLite 中的用户、场地、预约、物资、审计等表。可在「裸 SQL + 显式事务」与「ORM（SQLAlchemy）」之间选择。

## 决策

采用 **裸 SQL**（`sqlite3` + 手写 SQL），不引入 ORM。

理由：

1. 领域规则（半开区间冲突检测、状态机流转、审计留痕）本就是集合运算，手写 SQL 比 ORM 查询构造器更直白、更贴近业务语义。
2. 表结构稳定、关系简单（少量 JOIN），ORM 的迁移/懒加载/关系映射收益不明显。
3. `app/models.py` 以单一 `SCHEMA` 字符串集中定义 schema，配合 `transaction()` 上下文管理器，已足够清晰可控。

## 备选方案

- **SQLAlchemy ORM**：增加概念负担与依赖，且需为现有 SQL 重写，收益不匹配，否决。
- **SQLAlchemy Core**：介于两者之间，但当前规模用不上表达式构造器，否决。

## 后果

- 正面：零额外依赖，SQL 完全可见、可测试。
- 负面：缺少跨数据库方言抽象（本项目锁定 SQLite，无此需求）；无自动迁移。
- 数据访问约定：所有写操作经 `database.transaction(db)`；读操作用只读事务或直接查询。

## 附：索引与查询复杂度

- `reservation_schedule(venue_id, reserve_date, status, start_time, end_time)`：支撑场地排期与冲突检测（`overlapping_reservation`），O(log n) 定位候选后小范围扫描。
- `reservation_inventory(reserve_date, status, start_time, end_time)`：支撑物资可用量统计（`available_quantities`）。
- `reservation_owner(user_id, created_at)`：支撑「我的申请」列表。
- `venue_lock_schedule(venue_id, lock_date)`：支撑场地锁定冲突检测。
- `audit_reservation(reservation_id, id)`：支撑单条预约的审计履历。

在演示数据规模（数十条预约）下这些索引绰绰有余；若数据量增长，优先关注 `reservation_schedule` 与 `reservation_inventory` 的覆盖顺序。
