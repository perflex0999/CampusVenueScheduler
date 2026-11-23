# Roadmap

## 近期（1.x）

- [ ] CI/CD：GitHub Actions 流水线（lint + test + coverage 质量门禁）
- [ ] Docker 镜像打包，一条命令容器化运行
- [ ] 前端 `scheduler.js` 按「页面渲染 / API 封装 / 状态」拆分模块
- [ ] 语义化版本自动发布 + 自动生成 Release Notes

## 已完成

- [x] pytest 测试套件（单元 + 集成，约 90% 行覆盖率）
- [x] 应用工厂 `create_app` 与签名级类型标注
- [x] 全局 JSON 500 处理器、`MAX_CONTENT_LENGTH` 限制
- [x] 架构决策记录（`docs/adr/`）
- [x] 社区元文件：README / LICENSE(MIT) / CHANGELOG / CONTRIBUTING / CODE_OF_CONDUCT / SECURITY
- [x] 工程化配置：`.editorconfig`、`pyproject.toml`（ruff）、`requirements-dev.txt`
