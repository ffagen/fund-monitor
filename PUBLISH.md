# 📊 Fund Monitor 基金监控面板 - 发布说明

## 🆕 最新版本

**v1.0.0** - 2026-03-08

## 📦 安装方式

### 方式一：从 GitHub 安装（推荐）

```bash
npx skills add ffagen/fund-monitor -g -y
```

### 方式二：手动安装

```bash
# 克隆仓库
git clone https://github.com/ffagen/fund-monitor.git ~/.openclaw/skills/ffagen__fund-monitor
```

## 🚀 快速开始

```bash
# 安装依赖
pip install requests

# 启动服务
python3 ~/.openclaw/skills/ffagen__fund-monitor/fund_manager.py
```

访问 http://127.0.0.1:5001

## ✨ 新增功能 (v1.0)

- ✅ 实时估值获取（并发加速）
- ✅ 5分钟缓存
- ✅ 加仓/减仓功能
- ✅ T+1/T+2 自动计算
- ✅ 交易历史记录
- ✅ 基金代码显示
- ✅ 移动端适配

## ⚠️ 免责声明

1. **数据来源**: 本工具所有数据均来源于**公开网络接口**（天天基金网等公开API），不保证数据完整性、准确性和及时性
2. **投资风险**: 估值数据仅供**参考**，不构成任何投资建议。投资者据此操作，**风险自担**
3. **个人学习**: 本项目仅供**个人学习研究**之用，基于开源社区精神开发
4. **无商业担保**: 作者不对任何因使用本工具造成的直接或间接损失负责
5. **侵权联系**: 如有侵权，请联系删除

## 🙏 致谢

受 [FundVal-Live](https://github.com/Ye-Yu-Mo/FundVal-Live) 启发，感谢作者 [Ye-Yu-Mo](https://github.com/Ye-Yu-Mo) 的开源精神！

## 📁 文件结构

```
ffagen__fund-monitor/
├── SKILL.md           # OpenClaw 技能定义
├── fund_manager.py    # 主程序
└── README.md         # 中英双语文档
```

## 📄 开源协议

MIT License

---

## 💬 交流与反馈

- GitHub Issues: https://github.com/ffagen/fund-monitor/issues
- 欢迎 Star ⭐ 和 Fork 🍴

## 🔗 相关链接

- GitHub: https://github.com/ffagen/fund-monitor
- FundVal-Live: https://github.com/Ye-Yu-Mo/FundVal-Live
- OpenClaw: https://github.com/openclaw/openclaw
