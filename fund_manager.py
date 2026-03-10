#!/usr/bin/env python3
"""
基金估值计算器 v3
- 并发请求 + 5分钟缓存
- 加仓/减仓功能 + T+2计算
"""
import json
import os
import time
import requests
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

FUNDS = {
    "378006": "摩根全球新兴市场混合(QDII)A",
    "005534": "华夏新时代混合(QDII)人民币A",
    "012920": "易方达全球成长精选混合(QDII)A",
    "050015": "博时大中华亚太精选",
    "040018": "华夏新兴消费混合A",
    "007280": "广发创新升级混合A",
    "160125": "南方香港优选股票",
    "020743": "富国天盈债券A",
    "100055": "富国全球科技互联网股票(QDII)A",
    "017641": "易方达远见成长混合A",
    "006282": "摩根欧洲动力策略股票(QDII)A",
}

QDII_CODES = {'378006', '005534', '012920', '050015', '040018', '007280', '160125', '020743', '100055', '017641', '006282'}

HOLDINGS_FILE = os.path.expanduser('~/.openclaw/workspace/fund_holdings.json')
CACHE_FILE = os.path.expanduser('~/.openclaw/workspace/fund_cache.json')
TRADES_FILE = os.path.expanduser('~/.openclaw/workspace/fund_trades.json')

CACHE_TTL = 300

def load_holdings():
    """Load holdings, support both old format (amount) and new format (dict with amount/date/nav)"""
    try:
        with open(HOLDINGS_FILE, 'r') as f:
            raw = json.load(f)
        # Convert old format to new format
        converted = {}
        for code, value in raw.items():
            if isinstance(value, dict):
                converted[code] = value
            else:
                # Old format: just amount, assume purchase date is today
                converted[code] = {
                    'amount': value,
                    'purchase_date': datetime.now().strftime('%Y-%m-%d'),
                    'purchase_nav': None
                }
        return converted
    except:
        return {}

def save_holdings(data):
    with open(HOLDINGS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def fetch_historical_nav(fund_code, date_str):
    """Fetch NAV for a specific date"""
    try:
        url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://fund.eastmoney.com/'}
        r = requests.get(url, headers=headers, timeout=8)
        content = r.text
        
        nav_match = re.search(r'Data_netWorthTrend\s*=\s*(\[.*?\]);', content, re.DOTALL)
        if nav_match:
            nav_data = json.loads(nav_match.group(1))
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
            for item in reversed(nav_data):
                ts = item.get('x', 0) / 1000
                nav_date = datetime.fromtimestamp(ts)
                if nav_date.date() == target_date.date():
                    return item.get('y')
        return None
    except:
        return None

def load_trades():
    try:
        with open(TRADES_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_trades(data):
    with open(TRADES_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_cache():
    try:
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_cache(data):
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f)

def get_cache(key):
    cache = load_cache()
    if key in cache:
        cached = cache[key]
        if time.time() - cached['time'] < CACHE_TTL:
            return cached['data']
    return None

def set_cache(key, data):
    cache = load_cache()
    cache[key] = {'time': time.time(), 'data': data}
    save_cache(cache)

def calc_t2(is_qdii=False, trade_hour=None, trade_date=None):
    """计算T+2确认日期
    Args:
        is_qdii: 是否为QDII基金
        trade_hour: 交易时间的小时数（可选，默认用当前时间）
        trade_date: 交易日期的日期字符串 YYYY-MM-DD（可选，默认用当前日期）
    """
    # 如果传入了交易时间，用交易时间；否则用当前时间
    if trade_date:
        try:
            base_date = datetime.strptime(trade_date, '%Y-%m-%d')
        except:
            base_date = datetime.now()
    else:
        base_date = datetime.now()
    
    if trade_hour is not None:
        hour = trade_hour
    else:
        hour = base_date.hour
    
    if is_qdii or hour >= 15:
        # QDII基金或15点后：T+2
        t1 = base_date + timedelta(days=1)
        while t1.weekday() >= 5:
            t1 += timedelta(days=1)
        t2 = t1 + timedelta(days=1)
        while t2.weekday() >= 5:
            t2 += timedelta(days=1)
    else:
        # 普通基金15点前：T+1
        t1 = base_date + timedelta(days=1)
        while t1.weekday() >= 5:
            t1 += timedelta(days=1)
        t2 = None
    
    return {
        't1': t1.strftime('%m-%d'),
        't2': t2.strftime('%m-%d') if t2 else None,
        'is_qdii': is_qdii,
        'after_15': hour >= 15
    }

def fetch_fund_estimate(fund_code):
    try:
        url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
        r = requests.get(url, timeout=5)
        text = r.text
        if not text or text == 'jsonpgz();':
            return None
        match = re.search(r'jsonpgz\((.*)\);?', text)
        if match:
            data = json.loads(match.group(1))
            gsz = data.get('gsz')
            if not gsz:
                return None
            return {
                'estimate_nav': float(gsz),
                'estimate_growth': float(data.get('gszzl', 0)),
                'estimate_time': data.get('gztime', ''),
            }
    except:
        pass
    return None

def fetch_fund_data(fund_code):
    cache_key = f"fund_{fund_code}"
    cached = get_cache(cache_key)
    if cached:
        return cached
    
    estimate = fetch_fund_estimate(fund_code)
    url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
    try:
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://fund.eastmoney.com/'}
        r = requests.get(url, headers=headers, timeout=8)
        content = r.text
        data = {'code': fund_code, 'is_qdii': fund_code in QDII_CODES}
        
        name_match = re.search(r'fS_name\s*=\s*"([^"]+)"', content)
        if name_match:
            data['name'] = name_match.group(1)
        
        nav_match = re.search(r'Data_netWorthTrend\s*=\s*(\[.*?\]);', content, re.DOTALL)
        if nav_match:
            nav_data = json.loads(nav_match.group(1))
            if nav_data:
                data['nav'] = nav_data[-1]['y']
                data['yesterday_nav'] = nav_data[-2]['y'] if len(nav_data) >= 2 else nav_data[-1]['y']
                ts = nav_data[-1].get('x', 0) / 1000
                data['nav_date'] = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        
        year_match = re.search(r'syl_1n\s*=\s*"([^"]+)"', content)
        if year_match:
            data['year'] = year_match.group(1)
        
        if estimate:
            data['estimate_nav'] = estimate['estimate_nav']
            data['estimate_growth'] = estimate['estimate_growth']
            data['estimate_time'] = estimate['estimate_time']
        
        set_cache(cache_key, data)
        return data
    except Exception as e:
        return {'code': fund_code, 'error': str(e), 'is_qdii': fund_code in QDII_CODES}

def fetch_all_funds_concurrent():
    holdings = load_holdings()
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_code = {executor.submit(fetch_fund_data, code): code for code in FUNDS}
        for future in as_completed(future_to_code):
            code = future_to_code[future]
            try:
                fund_info = future.result()
                hold_amount = holdings.get(code, 0)
                today_change = None
                if fund_info.get('nav') and fund_info.get('yesterday_nav'):
                    today_change = round((fund_info['nav'] - fund_info['yesterday_nav']) / fund_info['yesterday_nav'] * 100, 2)
                
                # Calculate current value based on purchase NAV
                hold_info = holdings.get(code, {})
                hold_amount = hold_info.get('amount', 0) if isinstance(hold_info, dict) else hold_info
                purchase_nav = hold_info.get('purchase_nav') if isinstance(hold_info, dict) else None
                purchase_date = hold_info.get('purchase_date') if isinstance(hold_info, dict) else None
                
                # Calculate current value: shares = amount / purchase_nav, current_value = shares * current_nav
                current_value = None
                profit = None
                if hold_amount and purchase_nav and fund_info.get('estimate_nav'):
                    shares = hold_amount / purchase_nav
                    current_value = shares * fund_info['estimate_nav']
                    profit = current_value - hold_amount
                elif hold_amount and fund_info.get('estimate_nav'):
                    # No purchase NAV, can't calculate precisely
                    current_value = hold_amount
                
                results.append({
                    'code': code, 'name': fund_info.get('name', FUNDS.get(code, '')),
                    'nav': fund_info.get('nav'), 'yesterday_nav': fund_info.get('yesterday_nav'),
                    'today_change': today_change, 'year_gain': fund_info.get('year'),
                    'hold_amount': hold_amount, 'is_qdii': fund_info.get('is_qdii', False),
                    'nav_date': fund_info.get('nav_date', ''),
                    'estimate_nav': fund_info.get('estimate_nav'),
                    'estimate_growth': fund_info.get('estimate_growth'),
                    'estimate_time': fund_info.get('estimate_time'),
                    'current_value': current_value,
                    'profit': profit,
                    'purchase_date': purchase_date,
                    'purchase_nav': purchase_nav,
                })
            except:
                results.append({'code': code, 'name': FUNDS.get(code, '')})
    results.sort(key=lambda x: x['hold_amount'] or 0, reverse=True)
    return results

HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>基金持仓 - 净值版</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; padding: 0; }
        .header-bar { background: linear-gradient(135deg, #1678e1 0%, #1678e1 100%); color: white; padding: 20px 16px 30px; border-radius: 0 0 20px 20px; }
        .header-title { font-size: 14px; opacity: 0.9; margin-bottom: 8px; }
        .header-value { font-size: 32px; font-weight: bold; }
        .header-change { font-size: 14px; margin-top: 4px; }
        .stats { display: flex; gap: 12px; padding: 0 16px; margin-top: -20px; }
        .stat-card { flex: 1; background: white; border-radius: 12px; padding: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
        .stat-label { font-size: 12px; color: #999; margin-bottom: 4px; }
        .stat-value { font-size: 18px; font-weight: 600; color: #333; }
        .tips { background: #FFF7E6; border: 1px solid #FFD591; padding: 10px 12px; margin: 12px 16px; border-radius: 8px; font-size: 12px; color: #D46B08; }
        .actions { display: flex; gap: 10px; padding: 12px 16px; background: white; margin-top: 12px; }
        .btn { flex: 1; padding: 10px; border: none; border-radius: 8px; font-size: 14px; cursor: pointer; text-align: center; color: white; }
        .btn-primary { background: #1678e1; }
        .btn-success { background: #2ba471; }
        .btn-warning { background: #FA8C16; }
        .btn-danger { background: #ff4d4f; }
        .fund-list { padding: 0 16px; }
        .fund-item { background: white; border-radius: 12px; margin-bottom: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
        .fund-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; background: #fafafa; border-bottom: 1px solid #f0f0f0; }
        .fund-name { font-size: 14px; font-weight: 600; color: #333; }
        .fund-badge { display: inline-block; background: #FFF3E0; color: #FA8C16; padding: 2px 6px; border-radius: 4px; font-size: 10px; margin-left: 6px; }
        .fund-body { padding: 14px; }
        .fund-row { display: flex; justify-content: space-between; }
        .fund-col { text-align: center; flex: 1; }
        .fund-label { font-size: 11px; color: #999; margin-bottom: 4px; }
        .fund-val { font-size: 14px; font-weight: 500; }
        .fund-val.price { font-size: 16px; font-weight: 600; }
        .fund-val.red { color: #d91a1a; }
        .fund-val.green { color: #2ba471; }
        .fund-edit { display: flex; align-items: center; padding: 8px 14px; background: #f5f5f5; }
        .edit-label { font-size: 12px; color: #666; width: 60px; }
        .edit-input { flex: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
        .trade-btns { display: flex; gap: 8px; padding: 8px 14px; border-top: 1px solid #f0f0f0; }
        .trade-btn { flex: 1; padding: 8px; border: none; border-radius: 6px; font-size: 12px; cursor: pointer; color: white; }
        .trade-btn.buy { background: #ff4d4f; }
        .trade-btn.sell { background: #52c41a; }
        .modal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 100; align-items: center; justify-content: center; }
        .modal.show { display: flex; }
        .modal-content { background: white; padding: 24px; border-radius: 16px; width: 90%; max-width: 360px; }
        .modal-title { font-size: 18px; font-weight: 600; margin-bottom: 20px; }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; margin-bottom: 8px; font-size: 14px; color: #666; }
        .form-group input { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 16px; }
        .modal-btns { display: flex; gap: 12px; }
        .toast { position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: #333; color: white; padding: 12px 24px; border-radius: 8px; opacity: 0; transition: opacity 0.3s; z-index: 1000; }
        .toast.show { opacity: 1; }
        .refresh-time { text-align: center; padding: 12px; color: #999; font-size: 12px; }
        .t2-info { background: #e6f7ff; padding: 6px 10px; font-size: 11px; color: #1678e1; border-radius: 6px; margin-top: 6px; }
        .trade-history { background: #fafafa; padding: 8px 14px; font-size: 11px; color: #666; border-top: 1px solid #f0f0f0; }
    </style>
</head>
<body>
    <div class="header-bar">
        <div class="header-title">持仓总值</div>
        <div class="header-value" id="totalValue">--</div>
        <div class="header-change" id="totalChange">--</div>
    </div>
    <div class="stats">
        <div class="stat-card">
            <div class="stat-label">持仓金额</div>
            <div class="stat-value" id="totalAmount">--</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">持仓收益</div>
            <div class="stat-value" id="totalGain">--</div>
        </div>
    </div>
    <div class="tips">📈 估算净值（盘中更新）| ⚡ 并发加载中</div>
    <div class="actions">
        <button class="btn btn-warning" onclick="showAddModal()">➕ 添加基金</button>
        <button class="btn btn-primary" onclick="refresh()">🔄 刷新</button>
        <button class="btn btn-success" onclick="save()">💾 保存</button>
    </div>
    <div class="fund-list" id="fundList"><div style="text-align:center;padding:40px;color:#999;">加载中...</div></div>
    <div class="refresh-time" id="refreshTime"></div>
    
    <!-- 加仓/减仓 Modal -->
    <div class="modal" id="tradeModal">
        <div class="modal-content">
            <div class="modal-title" id="tradeTitle">➕ 加仓</div>
            <div class="form-group">
                <label>基金代码</label>
                <input type="text" id="tradeCode" readonly style="background:#f5f5f5;">
            </div>
            <div class="form-group">
                <label>金额（元）</label>
                <input type="number" id="tradeAmount" placeholder="如：10000">
            </div>
            <div class="form-group">
                <label>操作日期</label>
                <div style="display:flex;gap:8px;">
                    <input type="date" id="tradeDate" style="flex:2;padding:12px;border:1px solid #ddd;border-radius:8px;font-size:16px;">
                    <input type="time" id="tradeTime" value="09:30" style="flex:1;padding:12px;border:1px solid #ddd;border-radius:8px;font-size:16px;">
                </div>
            </div>
            <div class="t2-info" id="t2Info">T+1确认 (15点前)</div>
            <div class="modal-btns">
                <button class="btn" style="background:#999" onclick="hideTradeModal()">取消</button>
                <button class="btn btn-warning" onclick="submitTrade()">确认</button>
            </div>
        </div>
    </div>
    
    <!-- 添加基金 Modal -->
    <div class="modal" id="addModal">
        <div class="modal-content">
            <div class="modal-title">➕ 添加基金</div>
            <div class="form-group"><label>基金代码</label><input type="text" id="newFundCode" placeholder="6位代码"></div>
            <div class="form-group"><label>持仓金额</label><input type="number" id="newFundAmount" placeholder="如：10000"></div>
            <div class="form-group"><label>购买时间</label>
                <div style="display:flex;gap:8px;">
                    <input type="date" id="newFundDate" style="flex:2;padding:12px;border:1px solid #ddd;border-radius:8px;font-size:16px;">
                    <input type="time" id="newFundTime" value="09:30" style="flex:1;padding:12px;border:1px solid #ddd;border-radius:8px;font-size:16px;">
                </div>
            </div>
            <div class="t2-info" id="addT2Info">T+1确认 (15点前)</div>
            <div class="modal-btns"><button class="btn" style="background:#999" onclick="hideAddModal()">取消</button><button class="btn btn-warning" onclick="addFund()">添加</button></div>
        </div>
    </div>
    
    <div class="toast" id="toast"></div>
    <script>
        let fundData = [];
        let trades = {};
        let currentTradeType = 'buy';
        
        async function refresh() {
            document.getElementById('fundList').innerHTML = '<div style="text-align:center;padding:40px;color:#1678e1;">⚡ 加载中...</div>';
            try { 
                const res = await fetch('/api/funds'); 
                fundData = await res.json();
                const tradesRes = await fetch('/api/trades');
                trades = await tradesRes.json();
            } catch(e) { fundData = []; }
            render();
        }
        
        function getT2Info(code, timeStr) {
            const hour = parseInt(timeStr.split(':')[0]);
            const isQdii = fundData.find(f => f.code === code)?.is_qdii;
            if (isQdii || hour >= 15) {
                return 'T+2确认: 次日工作日 (QDII或15点后)';
            }
            return 'T+1确认: 当日工作日 (15点前)';
        }
        
        function render() {
            const list = document.getElementById('fundList');
            let totalAmount = 0, totalEstValue = 0;
            if (!fundData.length) {
                list.innerHTML = '<div style="text-align:center;padding:40px;color:#999;">暂无基金</div>';
                return;
            }
            list.innerHTML = fundData.map(f => {
                const amount = f.hold_amount || 0;
                // Use current_value from server if available, otherwise calculate
                const currentValue = f.current_value || (amount > 0 && f.yesterday_nav && f.estimate_nav ? (amount / f.yesterday_nav) * f.estimate_nav : amount);
                const profit = f.profit;
                totalAmount += amount; 
                totalEstValue += currentValue;
                
                const estGrowth = f.estimate_growth || 0;
                const estClass = estGrowth > 0 ? 'red' : estGrowth < 0 ? 'green' : '';
                const estStr = estGrowth >= 0 ? `+${estGrowth}%` : `${estGrowth}%`;
                const estBadge = f.estimate_nav ? '<span class="fund-badge" style="background:#e6f7ff;color:#1678e1;">估</span>' : '';
                const qdiiBadge = f.is_qdii ? '<span class="fund-badge">T+2</span>' : '';
                
                // Profit display
                const profitClass = profit > 0 ? 'red' : profit < 0 ? 'green' : '';
                const profitStr = profit !== null && profit !== undefined ? (profit >= 0 ? '+' : '') + profit.toLocaleString() : '--';
                const profitLabel = profit !== null && profit !== undefined ? '盈亏' : '持仓金额';
                
                // 交易记录
                const fundTrades = trades[f.code] || [];
                const tradeHtml = fundTrades.length > 0 ? '<div class="trade-history">最近: ' + fundTrades.slice(-3).map(t => 
                    `${t.type==='buy'?'➕':'➖'}${t.amount}元(${t.time})`
                ).join(' ') + '</div>' : '';
                
                // Purchase info
                const purchaseInfo = f.purchase_date ? `<span style="font-size:11px;color:#999;margin-left:8px;">买入:${f.purchase_date}</span>` : '';
                
                return `<div class="fund-item">
                    <div class="fund-header"><span class="fund-name">${f.code} ${f.name || f.code}${qdiiBadge}${estBadge}</span><span style="font-size:12px;color:#999;">${f.nav_date || '--'}${purchaseInfo}</span></div>
                    <div class="fund-body">
                        <div class="fund-row"><div class="fund-col"><div class="fund-label">估算净值</div><div class="fund-val price">${f.estimate_nav ? f.estimate_nav.toFixed(4) : '--'}</div></div>
                        <div class="fund-col"><div class="fund-label">估算涨跌</div><div class="fund-val ${estClass}" style="font-size:16px;font-weight:600;">${f.estimate_growth ? estStr : '--'}</div></div>
                        <div class="fund-col"><div class="fund-label">1年</div><div class="fund-val ${f.year_gain > 0 ? 'red' : 'green'}">${f.year_gain ? f.year_gain + '%' : '--'}</div></div></div>
                        <div class="fund-row" style="margin-top:10px"><div class="fund-col"><div class="fund-label">昨日净值</div><div class="fund-val">${f.yesterday_nav ? f.yesterday_nav.toFixed(4) : '--'}</div></div>
                        <div class="fund-col"><div class="fund-label">当前市值</div><div class="fund-val price">¥${currentValue.toLocaleString()}</div></div>
                        <div class="fund-col"><div class="fund-label">${profitLabel}</div><div class="fund-val price ${profitClass}">${profit !== null && profit !== undefined ? '¥' + profitStr : '¥' + amount.toLocaleString()}</div></div></div>
                    </div>
                    <div class="fund-edit"><span class="edit-label">持仓金额</span><input type="number" class="edit-input" data-code="${f.code}" value="${amount}"></div>
                    <div class="trade-btns">
                        <button class="trade-btn buy" onclick="showTradeModal('${f.code}', 'buy')">➕ 加仓</button>
                        <button class="trade-btn sell" onclick="showTradeModal('${f.code}', 'sell')">➖ 减仓</button>
                    </div>
                    ${tradeHtml}
                </div>`;
            }).join('');
            const gain = totalEstValue - totalAmount;
            document.getElementById('totalValue').textContent = '¥' + totalEstValue.toLocaleString();
            document.getElementById('totalChange').textContent = `估算 ${gain >= 0 ? '+' : ''}${gain.toLocaleString()}`;
            document.getElementById('totalAmount').textContent = '¥' + totalAmount.toLocaleString();
            const gainEl = document.getElementById('totalGain');
            gainEl.textContent = (gain >= 0 ? '+' : '') + gain.toLocaleString();
            gainEl.style.color = gain >= 0 ? '#d91a1a' : '#2ba471';
            document.getElementById('refreshTime').textContent = '更新时间: ' + new Date().toLocaleString();
        }
        
        function showTradeModal(code, type) {
            currentTradeType = type;
            document.getElementById('tradeTitle').textContent = type === 'buy' ? '➕ 加仓' : '➖ 减仓';
            document.getElementById('tradeCode').value = code;
            document.getElementById('tradeAmount').value = '';
            document.getElementById('tradeDate').value = new Date().toISOString().slice(0,10);
            document.getElementById('tradeTime').value = '09:30';
            document.getElementById('tradeModal').classList.add('show');
            updateTradeT2();
        }
        
        function hideTradeModal() {
            document.getElementById('tradeModal').classList.remove('show');
        }
        
        document.getElementById('tradeTime').addEventListener('change', updateTradeT2);
        document.getElementById('tradeDate').addEventListener('change', updateTradeT2);
        
        function updateTradeT2() {
            const timeStr = document.getElementById('tradeTime').value;
            const hour = parseInt(timeStr.split(':')[0]) || 9;
            const dateStr = document.getElementById('tradeDate').value;
            const date = dateStr ? new Date(dateStr) : new Date();
            
            // 计算下一个工作日（跳过周末）
            function getNextWorkday(d, daysToAdd) {
                const result = new Date(d);
                result.setDate(result.getDate() + daysToAdd);
                // 0=周日, 6=周六
                while (result.getDay() === 0 || result.getDay() === 6) {
                    result.setDate(result.getDate() + 1);
                }
                return result;
            }
            
            if (hour >= 15) {
                // T+2: 找后天的工作日
                const t2 = getNextWorkday(date, 2);
                const m2 = String(t2.getMonth() + 1).padStart(2, '0');
                const d2 = String(t2.getDate()).padStart(2, '0');
                document.getElementById('t2Info').textContent = 'T+2确认: ' + m2 + '-' + d2 + ' (15点后)';
            } else {
                // T+1: 找明天的工作日
                const t1 = getNextWorkday(date, 1);
                const m1 = String(t1.getMonth() + 1).padStart(2, '0');
                const d1 = String(t1.getDate()).padStart(2, '0');
                document.getElementById('t2Info').textContent = 'T+1确认: ' + m1 + '-' + d1 + ' (15点前)';
            }
        }
        
        async function submitTrade() {
            const code = document.getElementById('tradeCode').value;
            const amount = parseFloat(document.getElementById('tradeAmount').value);
            const dateStr = document.getElementById('tradeDate').value;
            const timeStr = document.getElementById('tradeTime').value;
            if (!amount || amount <= 0) { showToast('请输入金额'); return; }
            
            await fetch('/api/trade', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code, amount, type: currentTradeType, date: dateStr, time: timeStr})
            });
            showToast(currentTradeType === 'buy' ? '加仓成功' : '减仓成功');
            hideTradeModal();
            refresh();
        }
        
        async function save() {
            const holdings = {};
            document.querySelectorAll('.edit-input').forEach(i => { holdings[i.dataset.code] = parseFloat(i.value) || 0; });
            await fetch('/api/holdings', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(holdings)});
            showToast('保存成功！'); refresh();
        }
        
        function showAddModal() { document.getElementById('addModal').classList.add('show'); }
        function hideAddModal() { document.getElementById('addModal').classList.remove('show'); }
        
        document.getElementById('newFundTime').addEventListener('change', updateAddT2);
        document.getElementById('newFundDate').addEventListener('change', updateAddT2);
        
        function updateAddT2() {
            const timeStr = document.getElementById('newFundTime').value;
            const hour = parseInt(timeStr.split(':')[0]) || 9;
            const dateStr = document.getElementById('newFundDate').value;
            const date = dateStr ? new Date(dateStr) : new Date();
            
            // 计算下一个工作日（跳过周末）
            function getNextWorkday(d, daysToAdd) {
                const result = new Date(d);
                result.setDate(result.getDate() + daysToAdd);
                while (result.getDay() === 0 || result.getDay() === 6) {
                    result.setDate(result.getDate() + 1);
                }
                return result;
            }
            
            if (hour >= 15) {
                const t2 = getNextWorkday(date, 2);
                const m2 = String(t2.getMonth() + 1).padStart(2, '0');
                const d2 = String(t2.getDate()).padStart(2, '0');
                document.getElementById('addT2Info').textContent = 'T+2确认: ' + m2 + '-' + d2 + ' (15点后或QDII)';
            } else {
                const t1 = getNextWorkday(date, 1);
                const m1 = String(t1.getMonth() + 1).padStart(2, '0');
                const d1 = String(t1.getDate()).padStart(2, '0');
                document.getElementById('addT2Info').textContent = 'T+1确认: ' + m1 + '-' + d1 + ' (15点前)';
            }
        }
        
        async function addFund() {
            const code = document.getElementById('newFundCode').value.trim();
            const amount = parseFloat(document.getElementById('newFundAmount').value) || 0;
            const dateStr = document.getElementById('newFundDate').value || new Date().toISOString().slice(0,10);
            const timeStr = document.getElementById('newFundTime').value || '09:30';
            if(!code || !/^\\d{6}$/.test(code)) { showToast('请输入6位基金代码'); return; }
            const res = await fetch('/api/add_fund', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code, amount, date: dateStr, time: timeStr})});
            const d = await res.json();
            if(d.success) { showToast('添加成功'); hideAddModal(); refresh(); } else { showToast(d.error || '添加失败'); }
        }
        
        function showToast(msg) { const t = document.getElementById('toast'); t.textContent = msg; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'),2000); }
        refresh();
    </script>
</body>
</html>
'''

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode('utf-8'))
        elif parsed.path == '/api/funds':
            results = fetch_all_funds_concurrent()
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(results, ensure_ascii=False).encode('utf-8'))
        elif parsed.path == '/api/trades':
            trades = load_trades()
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(trades, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/api/holdings':
            length = int(self.headers.get('content-length', 0))
            data = self.rfile.read(length)
            holdings = json.loads(data.decode('utf-8'))
            save_holdings(holdings)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"success":true}')
        elif self.path == '/api/trade':
            length = int(self.headers.get('content-length', 0))
            data = self.rfile.read(length)
            req = json.loads(data.decode('utf-8'))
            code, amount, trade_type, time_str = req.get('code',''), req.get('amount',0), req.get('type','buy'), req.get('time','09:30')
            date_str = req.get('date', datetime.now().strftime('%Y-%m-%d'))
            
            # 解析交易时间
            trade_hour = 9
            try:
                trade_hour = int(time_str.split(':')[0])
            except:
                pass
            
            # 获取基金的QDII属性
            is_qdii = code in QDII_CODES
            
            # 计算确认日期
            t2_info = calc_t2(is_qdii, trade_hour, date_str)
            confirm_date = t2_info['t2'] or t2_info['t1']
            
            # 保存交易记录
            trades = load_trades()
            if code not in trades:
                trades[code] = []
            trades[code].append({
                'type': trade_type,
                'amount': amount,
                'date': date_str,
                'time': time_str,
                'confirm_date': confirm_date,
                'created': datetime.now().strftime('%Y-%m-%d %H:%M')
            })
            save_trades(trades)
            
            # 更新持仓 - 保留原有的购买日期和净值
            holdings = load_holdings()
            current = holdings.get(code, {})
            
            # 确保 current 是 dict 格式
            if not isinstance(current, dict):
                # 旧格式：只有金额，假设是今天买的
                current = {
                    'amount': current,
                    'purchase_date': datetime.now().strftime('%Y-%m-%d'),
                    'purchase_nav': None
                }
            
            current_amount = current.get('amount', 0)
            if trade_type == 'buy':
                current['amount'] = current_amount + amount
                # 如果没有购买记录，则记录本次购买的信息
                if not current.get('purchase_nav'):
                    # 尝试获取买入时的净值
                    purchase_nav = fetch_historical_nav(code, date_str)
                    if not purchase_nav:
                        # 获取不到则用昨日净值
                        fund_info = fetch_fund_data(code)
                        purchase_nav = fund_info.get('yesterday_nav')
                    current['purchase_date'] = date_str
                    current['purchase_nav'] = purchase_nav
            else:
                current['amount'] = max(0, current_amount - amount)
            
            holdings[code] = current
            save_holdings(holdings)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"success":true}')
        elif self.path == '/api/add_fund':
            length = int(self.headers.get('content-length', 0))
            data = self.rfile.read(length)
            req = json.loads(data.decode('utf-8'))
            code = req.get('code','')
            amount = req.get('amount',0)
            date_str = req.get('date', datetime.now().strftime('%Y-%m-%d'))
            time_str = req.get('time','09:30')
            fund_info = fetch_fund_data(code)
            if fund_info.get('error') or not fund_info.get('name'):
                self.send_response(400)
                self.send_header('Content-type','application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success':False,'error':'基金代码不存在'}).encode())
                return
            FUNDS[code] = fund_info.get('name',code)
            
            # Fetch historical NAV for the purchase date
            purchase_nav = fetch_historical_nav(code, date_str)
            if not purchase_nav:
                # If can't find exact date NAV, use yesterday's NAV
                purchase_nav = fund_info.get('yesterday_nav')
            
            holdings = load_holdings()
            holdings[code] = {
                'amount': amount,
                'purchase_date': date_str,
                'purchase_nav': purchase_nav
            }
            save_holdings(holdings)
            self.send_response(200)
            self.send_header('Content-type','application/json')
            self.end_headers()
            self.wfile.write(b'{"success":true}')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args): pass

def run_server():
    port = 5001
    server = HTTPServer(('0.0.0.0', port), Handler)
    print("=" * 50)
    print("🚀 基金持仓管理 v3 (加仓/减仓)")
    print("=" * 50)
    print(f"📍 http://localhost:{port}")
    print("=" * 50)
    server.serve_forever()

if __name__ == '__main__':
    run_server()
