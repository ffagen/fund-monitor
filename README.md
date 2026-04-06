# 📊 Fund Monitor

> 基金实时估值监控面板 | 加仓/减仓 | T+1/T+2 自动计算 | 盈亏一目了然

English | [中文](./README.md)

---

## ⚠️ Disclaimer / 免责声明

**This tool is for educational and informational purposes only. It does not constitute any investment advice.**

- All data is sourced from **public APIs** (e.g. Tencent Fund / 天天基金) — no guarantee of completeness, accuracy, or timeliness
- Intraday NAV estimates are **reference values only**; final settlement price is determined by the fund company's confirmed NAV
- **Investment decisions are made at your own risk.** The author shall not be liable for any direct or indirect losses arising from the use of this tool
- This project is provided for **personal learning** purposes only, developed in the spirit of the open-source community
- For any copyright concerns, please contact for removal

---

## ✨ Features

- ⚡ **Real-time Estimates** — Concurrent fetching of fund intraday estimated NAV
- 💾 **5-minute Cache** — Avoid redundant requests, faster response
- ➕➖ **Buy/Sell Recording** — Track each operation with time and amount
- 📅 **T+1/T+2 Auto-calculation** — Automatically determines confirmation date based on operation time (before/after 15:00) and fund type
- 💰 **PnL Calculation** — Current market value and profit/loss based on purchase NAV
- 📈 **Transaction History** — View buy/sell records for each fund
- 🎨 **Clean UI** — Mobile-friendly responsive design

## 🚀 Quick Start

### Install Dependencies

```bash
pip install requests
```

### Launch

```bash
python3 ~/.openclaw/skills/ffagen__fund-monitor/fund_manager.py
```

### Access

- Local: http://127.0.0.1:5001
- LAN: http://YOUR_IP:5001

## 📖 Usage

### Add Fund

Click "➕ 添加基金", enter:
- Fund code (6 digits)
- Amount held
- Purchase date and time

System will automatically fetch the NAV on the purchase date.

### Buy/Sell

Each fund has "➕ 加仓" (buy) and "➖ 减仓" (sell) buttons:
- Enter amount, date, and time
- System auto-calculates confirmation date
- Recorded in transaction history

## 📁 File Structure

```
ffagen__fund-monitor/
├── SKILL.md           # Skill definition
├── fund_manager.py    # Main program
└── README.md         # This file
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
