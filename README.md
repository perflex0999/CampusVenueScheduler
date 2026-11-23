# 校园多功能活动与场地协同调度系统

**CampusVenueScheduler** —— 一个零外部依赖、开箱即用的校园活动与场地协同调度系统。

用「单个 SQLite 文件 + 单个 Flask 进程」完整覆盖 `活动申报 → 场地预约 → 物资借调 → 两级审批 → 排期日历` 的闭环，以原生 JavaScript 单页应用交付：无需 Docker、无需独立数据库，两条命令即可本地运行。

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## ✨ 功能特性

- **活动申报**：学生/社团在线提交活动方案（草稿暂存 / 正式提交）。
- **场地预约**：按场地容量、开放时段校验，半开区间 `[start, end)` 冲突检测，背靠背时段互不冲突。
- **物资借调**：随预约附带设备借用，按「已批准占用」实时计算可借数量与单次限借。
- **两级审批**：指导教师初审（限本学院）→ 场地管理员终审，状态机 `草稿 → 待初审 → 待终审 → 已批准`。
- **排期日历**：按场地/日期查看占用、锁定与预约明细。
- **场地与物资管理**：场地增改、维护锁定/解锁，物资台账与库存。
- **账号与安全**：四类角色（学生/指导教师/场地管理员/系统管理员），会话认证 + `auth_version` 即时失效，连续 5 次登录失败锁定 5 分钟。
- **审计留痕**：全量操作审计日志，管理员可追溯与一键重置演示数据。

## 🚀 快速开始

```bash
# 1. 安装依赖（仅 Flask + Werkzeug）
python -m pip install -r requirements.txt

# 2. 启动服务（首次启动自动建库并灌入演示数据）
python -m scripts.run_server
```

浏览器访问 **http://127.0.0.1:8000** 即可登录。如需手动重置演示数据：

```bash
python -m scripts.init_db
```

## 🐳 Docker

```bash
docker build -t campus-venue-scheduler .
docker run -p 8000:8000 -v campus-venue-data:/app/var campus-venue-scheduler
```

访问 http://localhost:8000。镜像监听 `0.0.0.0:8000`，SQLite 数据持久化于命名卷 `campus-venue-data`。

## 👤 演示账号

| 账号 | 密码 | 角色 |
|---|---|---|
| `student_01` / `student_02` | `123456` | 学生 |
| `advisor_01` | `123456` | 指导教师 |
| `manager_01` | `123456` | 场地管理员 |
| `admin` | `admin123` | 系统管理员 |

## 🏗️ 架构概览

后端为「分层单体」：HTTP 层薄转发，业务逻辑集中在 service 层，数据访问走裸 SQL + 显式事务。

```text
浏览器（原生 JS 单页应用，hash 路由）
        │  JSON /api/*
        ▼
app/api.py          Flask Blueprint，路由与鉴权装饰器（薄转发）
        ▼
app/services/       业务逻辑：auth / booking / venue / equipment
        ▼
app/schemas.py      请求校验（ApiError 统一错误）
app/database.py     SQLite 连接 + transaction 上下文管理器
app/models.py       全量 schema（裸 SQL）+ 枚举 + 审计助手
```

- **数据**：SQLite（WAL 模式），`var/campus_scheduler.sqlite3`，无 ORM。
- **认证**：Flask 服务端 session + `users.auth_version` 失效机制。
- **前端**：原生 JS 单文件 SPA，无框架、无构建步骤。

## 📖 文档

| 文档 | 说明 |
|---|---|
| [快速开始](docs/quickstart.md) | 安装、启动、演示账号、测试命令 |
| [API 参考](docs/api.md) | 全部 REST 端点与权限说明 |
| [需求规格说明](docs/01_需求规格说明.md) | 业务功能与状态流转 |
| [技术与数据库设计](docs/02_技术与数据库设计.md) | 技术选型与表结构 |
| [部署与用户手册](docs/03_部署与用户手册.md) | 部署与使用指南 |
| [开发历程规范](docs/development-workflow.md) | 分支模型、提交规范、版本与发布闭环 |
| [架构决策记录](docs/adr/) | 关键技术决策（ADR） |

## 🧪 测试

```bash
python -m pip install -r requirements-dev.txt
python -m pytest                                  # 运行测试
python -m pytest --cov=app --cov-report=term-missing   # 含覆盖率（目标 ≥ 80%）
```

## 🤝 贡献

欢迎提交 Issue 与 Pull Request。请先阅读 [贡献指南](CONTRIBUTING.md) 与 [行为准则](CODE_OF_CONDUCT.md)。

## 📄 License

[MIT](LICENSE) © The CampusVenueScheduler Authors
