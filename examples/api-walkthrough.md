# API 调用示例（curl 走查）

以下用 `curl` 演示「学生提交 → 指导教师初审 → 场地管理员终审」的完整闭环。先启动服务（`python -m scripts.run_server`），默认地址 `http://127.0.0.1:8000`。

> 预约日期须晚于当前时间；示例中的 `<日期>` 请替换为未来日期（如 `2026-12-15`），`<预约id>` 替换为第 2 步返回的 `id`。

## 1. 学生登录

```bash
curl -s -c cookies.txt -H "Content-Type: application/json" -d '{"username":"student_01","password":"123456"}' http://127.0.0.1:8000/api/auth/login
```

## 2. 学生提交预约

```bash
curl -s -b cookies.txt -H "Content-Type: application/json" -d '{"title":"开源技术沙龙","type":"学术讲座","people":50,"venue":"ZJ-101","date":"<日期>","start":"14:00","end":"16:00","description":"面向学生的技术分享活动。","equipment":{"EQ-001":2}}' http://127.0.0.1:8000/api/reservations
```

## 3. 指导教师登录并初审

```bash
curl -s -c advisor.txt -H "Content-Type: application/json" -d '{"username":"advisor_01","password":"123456"}' http://127.0.0.1:8000/api/auth/login
curl -s -b advisor.txt -H "Content-Type: application/json" -d '{"decision":"APPROVED","comment":"同意举办，方案完整。"}' http://127.0.0.1:8000/api/approvals/<预约id>/audit
```

## 4. 场地管理员登录并终审

```bash
curl -s -c manager.txt -H "Content-Type: application/json" -d '{"username":"manager_01","password":"123456"}' http://127.0.0.1:8000/api/auth/login
curl -s -b manager.txt -H "Content-Type: application/json" -d '{"decision":"APPROVED","comment":"场地与物资已确认。"}' http://127.0.0.1:8000/api/approvals/<预约id>/audit
```

## 5. 查看排期

```bash
curl -s -b cookies.txt "http://127.0.0.1:8000/api/venues/ZJ-101/schedule?date=<日期>"
```

完整端点与参数见 [docs/api.md](../docs/api.md)。
