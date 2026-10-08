# 加密货币市场风险分析

[English](README.md) | 简体中文

这是一个面向风险分析、商业分析和金融科技岗位的作品集项目。项目从 Binance.US 获取 BTC/USDT 和 BNB/USDT 的 30 分钟 OHLCV 数据，使用 Parquet 保存中间数据，在 MySQL 中建立星型模型，并通过 Python 和 Tableau 分析收益率、波动率、风险收益关系与市场时间规律。

> 本项目仅用于学习和作品展示，不构成投资建议。

![加密货币市场风险分析概览](docs/risk_analytics_overview.png)

## 项目内容

- `src/`：API 数据获取和 MySQL 入库脚本
- `sql/`：数据库表结构与日频聚合脚本
- `data/processed/`：项目使用的 BTC、BNB Parquet 数据
- `notebooks/`：Python 探索性数据分析
- `tableau/`：Tableau 仪表板源文件
- `docs/`：项目演示文稿、数据架构图和 EER 图

数据覆盖 2022 年 11 月 1 日至 2025 年 10 月 31 日，每个币种包含 52,594 条 30 分钟记录。

## 主要发现

- BTC 样本期末的标准化收盘价约为起点的 5.36 倍，BNB 约为 3.36 倍。
- 按相邻日收盘价计算，BNB 的日收益波动率高于 BTC（2.83% 对 2.47%），因此不能用绝对价格高低比较风险。
- 两个币种的夏季平均日内收益均为负。BTC 的平均日内振幅在夏季最高，BNB 则在冬季最高。
- 两个币种的星期三平均日内收益最高，但历史规律不代表未来表现。

Tableau 的季节分析使用日内收益和日内振幅，Python Notebook 使用收盘到收盘的对数收益率与滚动波动率，避免混淆不同风险口径。

## 运行顺序

SQL 脚本需要 MySQL 8.0 或更高版本。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
mysql -u root -p < sql/schema.sql
python src/ingest_to_mysql.py
mysql -u root -p crypto_db < sql/daily_aggregation.sql
python src/validate_data.py
```

如需重新获取数据，先运行：

```bash
python src/fetch_market_data.py
```

最后打开 `notebooks/crypto_market_eda.ipynb` 查看 Python 分析，或打开 `tableau/crypto_market_dashboard.twb` 查看仪表板。Tableau 连接 MySQL 时可参考[官方说明](https://help.tableau.com/current/pro/desktop/en-us/examples_mysql.htm)。

完整项目背景和结论位于 `docs/project_presentation.pptx`。

## 数据质量与限制

- 两个币种都存在同一段源数据缺口：2023 年 2 月 6 日 04:30 至 12:00 UTC 之间缺少 14 根预期的 30 分钟蜡烛。
- 数据没有重复的币种/时间组合、必填字段空值、负数市场数据或 OHLC 逻辑错误。
- 结论仅描述 Binance.US 的本项目样本，不构成预测或投资建议。
- Tableau 文件连接本地 MySQL；README 中的风险概览图方便招聘者无需配置数据库即可查看核心结论。

## 我的贡献

作为 Risk Analyst，Jiayi Yao 负责定义收益率与波动率口径，对比 BTC 和 BNB 的月度、季节与星期风险收益规律，复核结论是否得到数据支持，并将分析结果整理为适合作品集展示的风险洞察与建议。
