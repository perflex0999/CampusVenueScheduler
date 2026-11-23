# Changelog

本项目所有显著变更均记录于此。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本遵循 [语义化版本 SemVer](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2026-11-23

### Added

- 首个功能完整版本：活动申报、场地预约、物资借调、两级审批、排期日历。
- 四类角色权限模型与会话认证（含 `auth_version` 失效、登录锁定）。
- 场地 / 物资 / 账号管理与审计日志、演示数据一键初始化与重置。
- pytest 测试套件（单元 + 集成），行覆盖率约 90%。
- 应用工厂 `create_app(database=...)`，移除模块级 `app` 的导入副作用。
- 全局 JSON 500 异常处理器与 `MAX_CONTENT_LENGTH` 限制。
- 服务层与 `schemas` / `database` 的签名级类型标注。
- `docs/adr/` 架构决策记录（4 篇）。
- README、LICENSE（MIT）、贡献指南、行为准则、SECURITY、ROADMAP 等社区元文件。
- ruff 工程化配置、`.editorconfig`、`.pre-commit-config.yaml`。
- GitHub Actions CI（lint + 多平台测试矩阵）与 Docker 打包。

### Changed

- 修正 `docs/` 与代码不一致的表述（FastAPI→Flask、Python 3.12→3.12+ 等）。
