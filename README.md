# Audit-Q 风控审计服务

这是一个基于 FastAPI 的风控审计示例项目，主要包含两类能力：

- 关系图半监督识别：基于账户关系图识别潜在风险团伙，并生成可视化页面。
- 逾期风险评分：使用 LightGBM 对贷款样本进行逾期概率打分，并输出 CSV 与图表。

## 功能概览

- `POST /semi`：半监督图算法识别风险账户
- `POST /overdue`：训练/加载模型并生成逾期评分结果
- `GET /graph`：访问静态图页面（`static/graph.html`）
- 静态资源挂载：`/static/*`

## 技术栈

- Python 3.10+
- FastAPI + Uvicorn
- pandas / scikit-learn / lightgbm
- networkx / plotly / matplotlib / seaborn
- PyMySQL

## 项目结构

```text
audit-q/
├── audit_service.py      # API 入口与核心逻辑
├── sql.py                # 数据读取与 SQL 逻辑
├── generate_html.py      # 图可视化页面生成
├── config.py             # 配置项（请勿提交真实密钥）
├── logger.py             # 日志封装
├── requirements.txt      # 依赖
├── cache/                # 模型缓存目录
└── static/               # 静态输出（CSV、图表、HTML）
```

## 快速开始

1. 创建并激活虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

3. 配置数据库与地址信息

请在 `config.py` 中填写你自己的配置，并确保使用脱敏信息或环境变量注入，不要把真实凭据提交到仓库。

示例（脱敏）：

```python
REMOTE_ADDR = "http://<your-host>/static/"
DB_CFG = {
    "host": "<db-host>",
    "port": 3306,
    "user": "<db-user>",
    "password": "<db-password>",
    "database": "<db-name>",
    "charset": "utf8mb4",
}
```

4. 启动服务

```bash
uvicorn audit_service:app --host 0.0.0.0 --port 8000 --reload
```

5. 访问接口文档

```text
http://127.0.0.1:8000/docs
```

## API 示例

### 1) 半监督图识别

请求：`POST /semi`

示例请求体：

```json
{
  "edges": [
    {
      "records": [
        {"id": 1, "from_acct": 1001, "to_acct": 1002, "amount": 5000, "label": 1},
        {"id": 2, "from_acct": 1002, "to_acct": 1003, "amount": 1200, "label": 0}
      ]
    }
  ]
}
```

返回内容包含：

- `risk_accounts`：风险账户列表
- `graph_url`：可视化页面地址

### 2) 逾期风险评分

请求：`POST /overdue`

返回内容包含：

- `result`：贷款打分明细
- `csv_url`：CSV 下载地址（输出到 `static/overdue_scores.csv`）
- `img_url`：高风险图表地址（输出到 `static/images/`）

## 安全与合规建议

- 不要在仓库中提交真实数据库地址、账号、密码、内网 IP、生产域名。
- 建议将敏感配置迁移到环境变量，并在代码中读取。
- 将缓存产物与中间输出（如模型文件、调试数据）加入 `.gitignore`。
- 对外共享前，检查日志、截图、CSV 是否包含真实个人或业务敏感数据。

## 常见问题

- `POST /overdue` 无结果：确认数据库连接、表结构与时间字段可用。
- 图页面无法访问：确认服务已启动且 `static` 目录挂载正常。
- 首次训练较慢：属于正常现象，后续会优先加载 `cache/` 下已保存模型。
