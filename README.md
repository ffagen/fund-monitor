# 📊 Fund Monitor

> 轻量级基金持仓管理面板 | 实时估值 | T+1/T+2 自动计算

English | [中文](./README_zh.md)

## ⚠️ 免责声明

- 本工具所有数据均来源于**公开网络接口**（天天基金网等），不保证数据准确性
- 估值数据仅供**参考**，不构成任何投资建议
- 投资者据此操作，**风险自担**
- 本项目为**个人学习**之用，基于开源社区精神开发
- 如有侵权，请联系删除

## ✨ Features

- ⚡ **Real-time Estimates** - Concurrent fetching of fund intraday estimated NAV
- 💾 **5-minute Cache** - Avoid redundant requests, faster response
- ➕➖ **Buy/Sell Recording** - Track each operation with time and amount
- 📅 **T+1/T-2 Auto-calculation** - Automatically determines confirmation date
- 📈 **Transaction History** - View buy/sell records for each fund

## 🚀 Quick Start

### Install Dependencies

```bash
pip install requests
```

### Launch

```bash
python3 fund_manager.py
```

### Access

- Local: http://127.0.0.1:5001
- LAN: http://YOUR_IP:5001

## 📖 Usage

### Add Fund

Click "➕ 添加基金", enter fund code, amount, date and time.

System will automatically determine T+1 or T+2 confirmation date.

### Buy/Sell

Each fund has "➕ 加仓" (buy) and "➖ 减仓" (sell) buttons.

## 🛠️ Tech Stack

- Python 3
- Built-in HTTP Server
- Concurrent Requests (concurrent.futures)
- 天天基金 API

## 🙏 Credits

Inspired by [FundVal-Live](https://github.com/Ye-Yu-Mo/FundVal-Live) by [Ye-Yu-Mo](https://github.com/Ye-Yu-Mo)

## 📄 License

MIT License

---

## 📊 基金监控面板

> 轻量级基金持仓管理面板 | 实时估值 | T+1/T+2 自动计算

## ⚠️ 免责声明

- **数据来源**: 本工具所有数据均来源于**公开网络接口**（天天基金网等公开API），不保证数据完整性、准确性和及时性
- **投资风险**: 估值数据仅供**参考参考**，不构成任何投资建议。投资者据此操作，**风险自担**
- **个人学习**: 本项目仅供**个人学习研究**之用，基于开源社区精神开发
- **无商业担保**: 作者不对任何因使用本工具造成的直接或间接损失负责
- **侵权联系**: 如有侵权，请联系删除

## ✨ 功能特性

- ⚡ **实时估值** - 并发获取基金盘中估算净值
- 💾 **5分钟缓存** - 避免重复请求，提升响应速度
- ➕➖ **加仓/减仓** - 记录每次操作的时间和金额
- 📅 **T+1/T+2自动计算** - 根据操作时间和基金类型自动判断
- 📈 **交易历史** - 查看每只基金的加仓/减仓记录

## 🚀 快速开始

### 安装依赖

```bash
pip install requests
```

### 启动

```bash
python3 fund_manager.py
```

### 访问

- 本地: http://127.0.0.1:5001
- 局域网: http://你的IP:5001

## 📖 使用说明

### 添加基金

点击「➕ 添加基金」，输入基金代码、金额、日期和时间。

系统会自动判断 T+1 或 T+2 确认日。

### 加仓/减仓

每只基金有「➕ 加仓」和「➖ 减仓」按钮。

## 🛠️ 技术栈

- Python 3
- 内置 HTTP Server
- 并发请求 (concurrent.futures)
- 天天基金 API

## 🙏 致谢

受 [FundVal-Live](https://github.com/Ye-Yu-Mo/FundVal-Live) 启发，感谢作者 [Ye-Yu-Mo](https://github.com/Ye-Yu-Mo) 的开源精神！

## 📄 许可证

MIT License
