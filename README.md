# 📊 Fund Monitor

> 轻量级基金持仓管理面板 | 实时估值 | T+1/T+2 自动计算

English | [中文](./README.md)

## ✨ Features

- ⚡ **Real-time Estimates** - Concurrent fetching of fund intraday estimated NAV
- 💾 **5-minute Cache** - Avoid redundant requests, faster response
- ➕➖ **Buy/Sell Recording** - Track each operation with time and amount
- 📅 **T+1/T+2 Auto-calculation** - Automatically determines confirmation date based on operation time (before/after 15:00) and fund type
- 📈 **Transaction History** - View buy/sell records for each fund
- 🎨 **Clean UI** - Mobile-friendly responsive design

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

Click "➕ 添加基金", enter:
- Fund code (6 digits)
- Holding amount
- Purchase date and time

System will automatically determine T+1 or T+2 confirmation date.

### Buy/Sell

Each fund has "➕ 加仓" (buy) and "➖ 减仓" (sell) buttons:
- Enter amount and operation time
- System auto-calculates confirmation date
- Records to transaction history

## 📁 Files

```
fund-monitor/
├── SKILL.md           # OpenClaw skill definition
├── fund_manager.py    # Main program
└── README.md          # This file
```

## 🛠️ Tech Stack

- Python 3
- Built-in HTTP Server
- Concurrent Requests (concurrent.futures)
- 天天基金 API

## 🙏 Credits

Inspired by [FundVal-Live](https://github.com/Ye-Yu-Mo/FundVal-Live) by [Ye-Yu-Mo](https://github.com/Ye-Yu-Mo)

## 📄 License

MIT License
