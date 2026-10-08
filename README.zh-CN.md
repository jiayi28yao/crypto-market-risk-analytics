# 加密市场波动率数据项目

[English](README.md) | 简体中文

这是一个完整的数据工程与分析作品集项目。项目从 Binance.US 获取 BTC/USDT 和 BNB/USDT 的 30 分钟 OHLCV 数据，使用 Parquet 保存中间数据，在 MySQL 中建立星型模型，并通过 Python 和 Tableau 分析价格、成交量、收益率与波动率。

> 本项目仅用于学习和作品展示，不构成投资建议。

![Tableau 仪表板预览](docs/dashboard_overview.png)

## 项目内容

- `src/`：API 数据获取和 MySQL 入库脚本
- `sql/`：数据库表结构与日频聚合脚本
- `data/processed/`：项目使用的 BTC、BNB Parquet 数据
- `notebooks/`：Python 探索性数据分析
- `tableau/`：Tableau 仪表板源文件
- `docs/`：项目演示文稿、数据架构图和 EER 图

## 运行顺序

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
mysql -u root -p < sql/schema.sql
python src/ingest_to_mysql.py
mysql -u root -p crypto_db < sql/daily_aggregation.sql
```

如需重新获取数据，先运行：

```bash
python src/fetch_market_data.py
```

最后打开 `notebooks/crypto_market_eda.ipynb` 查看 Python 分析，或打开 `tableau/crypto_market_dashboard.twb` 查看仪表板。Tableau 连接 MySQL 时可参考[官方说明](https://help.tableau.com/current/pro/desktop/en-us/examples_mysql.htm)。

完整项目背景和结论位于 `docs/project_presentation.pptx`。
