# 快速开始

## 环境要求

- Python 3.12+
- 主流现代浏览器（Edge / Chrome / Firefox）

## 安装与启动

```bash
# 安装运行时依赖（仅 Flask + Werkzeug）
python -m pip install -r requirements.txt

# 启动服务（首次启动自动建库并灌入演示数据）
python -m scripts.run_server
```

浏览器访问 **http://127.0.0.1:8000**。

## 演示账号

| 账号 | 密码 | 角色 |
|---|---|---|
| `student_01` / `student_02` | `123456` | 学生 |
| `advisor_01` | `123456` | 指导教师 |
| `manager_01` | `123456` | 场地管理员 |
| `admin` | `admin123` | 系统管理员 |

## 数据初始化与重置

```bash
# 强制重置数据库到演示数据（清空现有业务数据）
python -m scripts.init_db
```

数据库文件位于 `var/campus_scheduler.sqlite3`（已被 `.gitignore` 忽略）。管理员也可在「数据初始化」页面一键重置。

## Docker 运行

```bash
docker build -t campus-venue-scheduler .
docker run -p 8000:8000 -v campus-venue-data:/app/var campus-venue-scheduler
```

镜像监听 `0.0.0.0:8000`，SQLite 数据持久化于命名卷 `campus-venue-data`。

## 运行测试

```bash
python -m pip install -r requirements-dev.txt
python -m pytest                                  # 运行全部测试
python -m pytest --cov=app --cov-report=term-missing   # 含覆盖率（目标 ≥ 80%）
```

## 代码检查

```bash
ruff check .        # lint
ruff format .       # 格式化
```

更多细节见 [API 参考](api.md) 与 [架构决策记录](adr/)。
