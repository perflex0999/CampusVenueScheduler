# CampusVenueScheduler v1.0.0 发布公告（草稿）

> 用途：可粘贴到 GitHub Release 正文，或改写为掘金 / 知乎帖子。

## 一句话

一个零外部依赖、开箱即用的校园活动与场地协同调度系统——用「单文件 SQLite + 单个 Flask 进程」覆盖 `活动申报 → 场地预约 → 物资借调 → 两级审批 → 排期日历` 全流程，原生 JS 单页应用交付，无需 Docker、无需独立数据库。

## 本次发布亮点

- **完整业务闭环**：活动申报、场地预约、物资借调、两级审批、排期日历。
- **四类角色权限模型**：学生 / 指导教师 / 场地管理员 / 系统管理员。
- **可靠的时间与冲突处理**：半开区间 `[start, end)` 冲突检测，背靠背时段互不冲突。
- **账号安全**：会话认证 + `auth_version` 即时失效，连续 5 次登录失败锁定 5 分钟。
- **工程化**：约 90% 行覆盖率的 pytest 测试套件、ruff 工程化、GitHub Actions CI。
- **零依赖部署**：`pip install` 两条命令运行，或 Docker 一键启动。

## 快速开始

```bash
git clone https://github.com/perflex0999/CampusVenueScheduler.git
cd CampusVenueScheduler
python -m pip install -r requirements.txt
python -m scripts.run_server
```

访问 http://127.0.0.1:8000，演示账号见 [README](../README.md)。

## 传播文案（掘金 / 知乎引言）

> 你有没有想过，一个「活动申报 → 场地预约 → 物资借调 → 两级审批 → 排期日历」的完整系统，可以零外部依赖、两条命令跑起来？CampusVenueScheduler 用单文件 SQLite 和一个 Flask 进程做到了，还附带 90% 覆盖率的测试与 Docker 支持。它刻意保持极简，把复杂度收敛到领域规则本身——适合教学演示，也适合中小场景二次开发。

## 提交到 awesome-list 的建议条目

```markdown
- [CampusVenueScheduler](https://github.com/perflex0999/CampusVenueScheduler) - 零依赖的校园活动与场地协同调度系统（Flask + SQLite + 原生 JS），含两级审批与排期日历。
```
