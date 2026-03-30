#!/usr/bin/env python3
"""
基金持仓分析脚本
基于 fund_watcher.py 的数据，进行持仓配置分析、问题诊断和优化建议
"""
import json
import sys
import os
from datetime import datetime

# ====== 基金分类配置 ======
FUND_CATEGORIES = {
    # 债券基金（低风险）
    "003949": {"name": "兴全稳泰债券A", "category": "债券", "risk": "低", "currency": "CNY"},
    "006662": {"name": "易方达安悦超短债A", "category": "债券", "risk": "低", "currency": "CNY"},
    "007744": {"name": "长盛安逸纯债债券A", "category": "债券", "risk": "低", "currency": "CNY"},
    # QDII基金（海外，高风险）
    "017641": {"name": "摩根标普500指数(QDII)", "category": "QDII", "risk": "高", "currency": "USD", "market": "美股"},
    "012920": {"name": "易方达全球成长精选混合(QDII)", "category": "QDII", "risk": "高", "currency": "混合", "market": "全球"},
    "539002": {"name": "建信新兴市场混合(QDII)", "category": "QDII", "risk": "高", "currency": "混合", "market": "新兴市场"},
    "457001": {"name": "国富亚洲机会股票(QDII)", "category": "QDII", "risk": "高", "currency": "混合", "market": "亚洲"},
    "378006": {"name": "摩根全球新兴市场混合(QDII)", "category": "QDII", "risk": "高", "currency": "混合", "market": "新兴市场"},
    "118001": {"name": "易方达亚洲精选股票", "category": "QDII", "risk": "高", "currency": "USD", "market": "亚洲"},
    "050015": {"name": "博时大中华亚太精选", "category": "QDII", "risk": "中高", "currency": "混合", "market": "大中华"},
    # 港股基金（中风险）
    "021046": {"name": "平安港股通红利精选", "category": "港股", "risk": "中高", "currency": "HKD", "market": "港股"},
    # A股/商品基金
    "000216": {"name": "华安黄金ETF联接A", "category": "商品", "risk": "中高", "currency": "CNY", "market": "黄金"},
    "023917": {"name": "华夏国证自由现金流ETF联接", "category": "A股", "risk": "中", "currency": "CNY", "market": "A股"},
    "009051": {"name": "易方达中证红利ETF联接", "category": "A股", "risk": "中", "currency": "CNY", "market": "A股红利"},
    "008163": {"name": "南方标普红利低波50ETF联接", "category": "A股", "risk": "中", "currency": "CNY", "market": "A股红利"},
    "008279": {"name": "国泰中证煤炭ETF联接A", "category": "商品", "risk": "高", "currency": "CNY", "market": "煤炭"},
}

# QDII基金列表（净值有延迟）
QDII_CODES = {"017641", "012920", "539002", "457001", "378006", "118001", "050015"}

# ====== 持仓数据 ======
HOLDINGS_FILE = os.path.expanduser('~/.openclaw/workspace/fund_holdings.json')


def load_holdings():
    """加载持仓"""
    try:
        if os.path.exists(HOLDINGS_FILE):
            with open(HOLDINGS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"读取持仓失败: {e}", file=sys.stderr)
    return {}


def load_fund_watcher_data():
    """从 fund_watcher.py 获取实时数据（JSON格式）"""
    import subprocess
    try:
        result = subprocess.run(
            [sys.executable, 
             os.path.join(os.path.dirname(__file__), "fund_watcher.py"), 
             "--json"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"调用 fund_watcher.py 失败: {e}", file=sys.stderr)
    return []


def analyze_portfolio(funds_data, holdings):
    """分析持仓结构"""
    categories = {}
    issues = []
    recommendations = []
    total_value = 0
    total_cost = 0

    for fund in funds_data:
        code = fund.get('code', '')
        if code not in FUND_CATEGORIES:
            continue

        info = FUND_CATEGORIES[code]
        nav = fund.get('nav') or 0
        yesterday_nav = fund.get('yesterday_nav') or nav
        today_change = fund.get('today_change') or 0
        hold_amount = holdings.get(code, 0)

        if hold_amount <= 0 or yesterday_nav <= 0:
            continue

        # 估算当前价值
        shares = hold_amount / yesterday_nav
        current_value = shares * nav
        profit = current_value - hold_amount
        profit_pct = (profit / hold_amount * 100) if hold_amount > 0 else 0

        total_value += current_value
        total_cost += hold_amount

        cat = info['category']
        if cat not in categories:
            categories[cat] = {"amount": 0, "count": 0, "profit": 0, "funds": []}
        categories[cat]["amount"] += current_value
        categories[cat]["count"] += 1
        categories[cat]["profit"] += profit
        categories[cat]["funds"].append({
            "code": code,
            "name": info['name'],
            "current_value": current_value,
            "cost": hold_amount,
            "profit": profit,
            "profit_pct": profit_pct,
            "today_change": today_change,
            "risk": info['risk'],
            "is_qdii": code in QDII_CODES,
        })

    # ====== 问题诊断 ======
    if total_value <= 0:
        return None

    # 问题1：QDII占比过高
    qdii_amount = categories.get("QDII", {}).get("amount", 0)
    qdii_ratio = qdii_amount / total_value * 100
    if qdii_ratio > 30:
        issues.append({
            "type": "over_concentration",
            "severity": "high",
            "title": "QDII占比过高",
            "detail": f"QDII基金合计占比 {qdii_ratio:.1f}%，超过建议上限30%，海外市场波动较大时容易大幅回撤",
            "data": f"当前QDII金额: {qdii_amount:,.0f}元，占比{qdii_ratio:.1f}%"
        })
        recommendations.append({
            "action": "reduce",
            "category": "QDII",
            "target_ratio": "20-25%",
            "detail": "建议保留2-3只长期业绩优秀的QDII，其余赎回转配置"
        })

    # 问题2：黄金占比过高（仅计算黄金，煤炭单独算）
    gold_fund = [f for cat_data in categories.values() 
                 for f in cat_data.get("funds", []) 
                 if FUND_CATEGORIES.get(f['code'], {}).get('market') == '黄金']
    gold_amount = sum(f['current_value'] for f in gold_fund)
    gold_ratio = gold_amount / total_value * 100 if total_value > 0 else 0
    coal_fund = [f for cat_data in categories.values() 
                 for f in cat_data.get("funds", []) 
                 if FUND_CATEGORIES.get(f['code'], {}).get('market') == '煤炭']
    coal_amount = sum(f['current_value'] for f in coal_fund)
    if gold_ratio > 15:
        issues.append({
            "type": "over_concentration",
            "severity": "medium",
            "title": "黄金/商品占比偏高",
            "detail": f"黄金持仓占比 {gold_ratio:.1f}%，超过建议上限15%，黄金适合对冲不宜重仓",
            "data": f"当前黄金金额: {gold_amount:,.0f}元，占比{gold_ratio:.1f}%；煤炭金额: {coal_amount:,.0f}元"
        })
        recommendations.append({
            "action": "reduce",
            "category": "黄金",
            "target_ratio": "8-10%",
            "detail": "建议减仓黄金，增加红利低波或债券基金提升稳定性"
        })

    # 问题3：债券占比偏低
    bond_amount = categories.get("债券", {}).get("amount", 0)
    bond_ratio = bond_amount / total_value * 100
    if bond_ratio < 20:
        issues.append({
            "type": "low_allocation",
            "severity": "medium",
            "title": "债券配置偏低",
            "detail": f"债券基金占比仅 {bond_ratio:.1f}%，建议提升至20-25%作为组合稳定器",
            "data": f"当前债券金额: {bond_amount:,.0f}元，占比{bond_ratio:.1f}%"
        })
        recommendations.append({
            "action": "increase",
            "category": "债券",
            "target_ratio": "20-25%",
            "detail": "建议增加债券基金，提升组合抗波动能力"
        })

    # 问题4：QDII基金今日普遍下跌检测（使用today_change，不是profit）
    qdii_funds = categories.get("QDII", {}).get("funds", [])
    losing_qdii = [f for f in qdii_funds if f['today_change'] < 0]
    if len(losing_qdii) >= 3:
        issues.append({
            "type": "multiple_losses",
            "severity": "high",
            "title": "多只QDII同时亏损",
            "detail": f"{len(losing_qdii)}只QDII基金今日净值下跌，今日合计拖累组合表现",
            "data": "\n".join([f"{f['name']} 今日{f['today_change']:+.2f}%" for f in qdii_funds])
        })

    # 问题5：小金额基金
    small_funds = [(cat, funds) for cat, data in categories.items() 
                   for funds in data.get("funds", []) 
                   if funds['current_value'] < 100]
    if small_funds:
        issues.append({
            "type": "tiny_position",
            "severity": "low",
            "title": "存在小额基金",
            "detail": "部分基金持仓金额过小，意义不大，建议清仓",
            "data": "\n".join([f"{f['name']}: {f['current_value']:.0f}元" for _, f in small_funds])
        })
        for _, f in small_funds:
            recommendations.append({
                "action": "clear",
                "code": f['code'],
                "name": f['name'],
                "detail": f"金额仅{f['current_value']:.0f}元，建议清仓"
            })

    # 今日亏损最多和盈利最多的基金
    all_funds_flat = [f for cat_data in categories.values() for f in cat_data.get("funds", [])]
    if all_funds_flat:
        worst = min(all_funds_flat, key=lambda x: x['today_change'])
        best = max(all_funds_flat, key=lambda x: x['today_change'])
    else:
        worst = best = None

    return {
        "total_value": total_value,
        "total_cost": total_cost,
        "total_profit": total_value - total_cost,
        "total_profit_pct": (total_value - total_cost) / total_cost * 100 if total_cost > 0 else 0,
        "categories": categories,
        "issues": issues,
        "recommendations": recommendations,
        "today_highlight": {
            "best": best,
            "worst": worst
        },
        "qdii_delay_note": "QDII基金净值基于海外上一个交易日收盘数据，存在1-2天延迟"
    }


def output_report(analysis, holdings):
    """输出分析报告（人类可读格式）"""
    if not analysis:
        print("❌ 无法获取分析数据", file=sys.stderr)
        return

    total = analysis['total_value']
    total_cost = analysis['total_cost']
    total_profit = analysis['total_profit']
    profit_pct = analysis['total_profit_pct']
    categories = analysis['categories']
    issues = analysis['issues']
    recommendations = analysis['recommendations']

    print()
    print("=" * 70)
    print(f"📊 基金持仓配置分析报告 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # 一、持仓结构
    print()
    print("【一、持仓结构】")
    print(f"{'类别':<8} {'金额(元)':>12} {'占比':>8} {'今日收益':>10} {'风险':<6}")
    print("-" * 50)
    for cat in ["债券", "QDII", "港股", "A股", "商品"]:
        if cat in categories:
            amt = categories[cat]["amount"]
            pct = amt / total * 100
            prof = categories[cat]["profit"]
            # 该类别风险等级（取最高的）
            risks = [f['risk'] for f in categories[cat]["funds"]]
            risk_display = "高" if "高" in risks else ("中" if "中" in risks else "低")
            print(f"{cat:<8} {amt:>12,.0f} {pct:>7.1f}% {prof:>+10,.0f} {risk_display:<6}")

    print("-" * 50)
    print(f"{'合计':<8} {total:>12,.0f} {'100.0%':>8} {total_profit:>+10,.0f}")

    # 二、QDII延迟说明
    print()
    print("【二、⚠️ QDII净值延迟提示】")
    qdii_funds = categories.get("QDII", {}).get("funds", [])
    if qdii_funds:
        print(f"共 {len(qdii_funds)} 只QDII基金，净值基于海外上一个交易日收盘数据，存在1-2天延迟：")
        for f in qdii_funds:
            market = FUND_CATEGORIES.get(f['code'], {}).get('market', '')
            print(f"  • {f['name']} → {market}市场，今日显示涨跌幅为上一交易日数据")

    # 三、问题诊断
    print()
    print("【三、⚠️ 问题诊断】")
    if not issues:
        print("  未发现明显问题 ✅")
    else:
        for i, issue in enumerate(issues, 1):
            severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(issue['severity'], "⚪")
            print(f"  {severity_icon} {i}. 【{issue['title']}】")
            print(f"     {issue['detail']}")
            if issue.get('data'):
                for line in issue['data'].split('\n'):
                    print(f"     └ {line}")

    # 四、优化建议
    print()
    print("【四、✅ 优化建议】")
    if not recommendations:
        print("  持仓结构良好，无需调整 ✅")
    else:
        # 按动作分组
        reduce_recs = [r for r in recommendations if r['action'] == 'reduce']
        increase_recs = [r for r in recommendations if r['action'] == 'increase']
        clear_recs = [r for r in recommendations if r['action'] == 'clear']

        if reduce_recs:
            print("  📉 减仓建议：")
            for r in reduce_recs:
                print(f"     • {r['detail']}")
                print(f"       目标占比: {r['target_ratio']}")

        if increase_recs:
            print("  📈 加仓建议：")
            for r in increase_recs:
                print(f"     • {r['detail']}")
                print(f"       目标占比: {r['target_ratio']}")

        if clear_recs:
            print("  🗑️ 清仓建议：")
            for r in clear_recs:
                print(f"     • {r['name']} ({r['code']}) - {r['detail']}")

    # 五、今日亮点
    print()
    print("【五、📌 今日亮点】")
    best = analysis['today_highlight']['best']
    worst = analysis['today_highlight']['worst']
    if best:
        print(f"  🟢 涨幅最大：{best['name']} 今日 +{best['today_change']:.2f}%")
    if worst:
        is_qdii_note = " (QDII净值滞后，以上为海外上一交易日数据)" if worst.get('is_qdii') else ""
        print(f"  🔴 跌幅最大：{worst['name']} 今日 {worst['today_change']:.2f}%{is_qdii_note}")

    # 六、总结
    print()
    print("【六、💡 综合评价】")
    if len([i for i in issues if i['severity'] == 'high']) == 0:
        print(f"  当前组合整体平衡，总收益 {total_profit:+.0f}元 ({profit_pct:+.2f}%)")
        print(f"  主要风险：QDII集中度偏高，建议逐步优化配置")
    else:
        print(f"  组合存在 {len([i for i in issues if i['severity'] == 'high'])} 项高风险问题，建议优先处理")

    print()
    print("=" * 70)
    print(f"💰 总本金: {total_cost:,.0f}元  →  现市值: {total:,.0f}元  |  总收益: {total_profit:+,.0f}元 ({profit_pct:+.2f}%)")
    print("=" * 70)
    print()


def output_json(analysis):
    """输出JSON格式数据"""
    print(json.dumps(analysis, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='基金持仓分析')
    parser.add_argument('--json', action='store_true', help='输出JSON格式')
    args = parser.parse_args()

    holdings = load_holdings()
    funds_data = load_fund_watcher_data()
    
    if not funds_data:
        print("❌ 无法获取基金数据，请先确保 fund_watcher.py 可正常运行", file=sys.stderr)
        sys.exit(1)

    analysis = analyze_portfolio(funds_data, holdings)

    if args.json:
        output_json(analysis)
    else:
        output_report(analysis, holdings)
