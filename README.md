# 本地股市分析程序

一个个人使用的本地 Web 工具，用日线行情生成价格走势、均线、RSI、52周区间和简单技术面评分。

## 功能

- 本地部署：使用 Python 标准库启动 HTTP 服务
- 股票查询：默认通过 Yahoo Finance chart 接口读取日线数据
- 本地缓存：相同股票和周期会缓存约 15 分钟，也可以批量预先缓存
- 技术指标：SMA20、SMA50、SMA200、RSI14、成交量均线
- 页面分析：关键指标、价格图、信号解释、最近交易日表格

## 运行

当前机器没有把 Python 加到 PATH，可以直接用 Codex 自带 Python：

```powershell
& 'C:\Users\cwu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' app.py
```

然后打开：

```text
http://127.0.0.1:8765
```

如果你的电脑已经安装了 Python，也可以：

```powershell
python app.py
```

### WSL 运行

在 WSL 里进入项目目录：

```sh
cd /mnt/d/workspace/finance/stock_analysis
```

确认 Python 可用：

```sh
python3 --version
```

启动服务：

```sh
sh run.sh
```

然后在 Windows 或 WSL 浏览器打开：

```text
http://localhost:8765
```

如果 Windows 浏览器访问不到 WSL 里的服务，可以改成监听所有本地网卡：

```sh
HOST=0.0.0.0 sh run.sh
```

## 股票代码示例

- 美股：`AAPL`、`MSFT`、`NVDA`
- 港股：Yahoo 常用后缀是 `.HK`，例如 `0700.HK`

## 预先缓存股票数据

批量缓存不会自动下载全球所有股票。它会读取 `symbols.xlsx` 里的股票池，然后逐个请求 Yahoo Finance 并写入 `.cache/`。如果没有 `symbols.xlsx`，`update_cache.sh` 会退回读取 `symbols.txt`。

编辑股票池：

```text
symbols.xlsx
```

Excel 使用不同工作表区分市场，例如：

```text
US
HK
```

每个工作表暂时只需要三列：

```text
symbol | name | enabled
```

`enabled` 填 `FALSE`、`0`、`no`、`disabled` 或 `停用` 时，该行会被跳过。示例：

```text
US sheet
symbol   name          enabled
AAPL     Apple         TRUE
MSFT     Microsoft     TRUE
SPY      S&P 500 ETF   TRUE

HK sheet
symbol   name          enabled
0700.HK  Tencent       TRUE
9988.HK  Alibaba HK    TRUE
```

在 WSL 里手动刷新缓存：

```sh
cd /mnt/d/workspace/finance/stock_analysis
sh update_cache.sh
```

指定旧的文本股票池也可以：

```sh
SYMBOLS_FILE=symbols.txt sh update_cache.sh
```

默认每日更新会维护每只股票一份 3 年基础日线缓存。Sigma Model 只生成最新交易日的一份预计算截面；单股分析页的 3 个月、6 个月、1 年等周期会直接从这份 3 年缓存里本地切片。

只更新港股：

```sh
MARKETS=HK sh update_cache.sh
```

只更新美股：

```sh
MARKETS=US sh update_cache.sh
```

网页里的 `Sigma Model` 页面也使用同一份 `symbols.xlsx`。顶部有全局市场下拉框，例如：

- 市场填 `HK`：只计算港股
- 市场填 `US`：只计算美股
- 市场留空：计算所有工作表里的股票

Sigma Model 结果里的 `LRC Z-score` 来自 200 日 Linear Regression Channel：

```text
(最新收盘价 - 线性回归趋势值) / 回归残差标准差
```

每日更新会预先生成：

```text
.cache/batch_results.json
```

其中包含 `代碼`、`LRC Z-score`、`名稱`、`最新價`、`漲跌額`、`漲跌幅`、`成交量`、`成交額`、`MA200`、`RSI14`、`MA50`、`開市`、`前收`、`最高`、`最低`、`量比`、`振幅`、多周期涨跌幅等字段。当前 Yahoo chart 数据源拿不到的盘口、行业和部分财务字段会保留为空值，后续接入更完整数据源后可以直接填充。

更新结果会写入：

```text
.cache/cache_report.csv
```

### 每天自动更新

在 WSL 里打开 crontab：

```sh
crontab -e
```

例如每天香港时间早上 7:30 更新一次：

```cron
30 7 * * * cd /mnt/d/workspace/finance/stock_analysis && /bin/sh update_cache.sh >> .cache/cron.log 2>&1
```

如果你用的是 Windows 任务计划程序，也可以让它每天执行：

```text
wsl -e sh -lc "cd /mnt/d/workspace/finance/stock_analysis && sh update_cache.sh"
```

## 测试

```powershell
& 'C:\Users\cwu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests
```

## 说明

这个工具只做研究和记录，不构成投资建议。Yahoo Finance 的非官方接口适合个人轻量使用；如果之后要接入稳定生产数据源，可以替换 `stock_analyzer/data.py` 里的 provider。
