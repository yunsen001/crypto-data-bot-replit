import asyncio
import logging
from datetime import datetime, timedelta
from exchange_api import get_order_book, get_recent_trades, get_price

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 大单阈值（美元）
LARGE_ORDER_THRESHOLD = 100000

async def analyze_fund_flow(symbol, exchange="binance"):
    """分析资金流向"""
    try:
        # 获取最近成交记录
        trades = await get_recent_trades(symbol, 1000, exchange)
        
        # 获取当前价格
        price_data = await get_price(symbol, exchange)
        current_price = price_data["price"]
        
        # 按时间段分组
        now = datetime.now()
        time_periods = {
            "15m": now - timedelta(minutes=15),
            "1h": now - timedelta(hours=1),
            "4h": now - timedelta(hours=4),
            "24h": now - timedelta(hours=24)
        }
        
        # 初始化结果
        results = {
            "symbol": symbol,
            "current_price": current_price,
            "institutional": {period: {"inflow": 0, "outflow": 0, "net_flow": 0} for period in time_periods},
            "retail": {period: {"inflow": 0, "outflow": 0, "net_flow": 0} for period in time_periods},
            "timestamp": now.timestamp()
        }
        
        # 分析每笔交易
        for trade in trades:
            trade_time = datetime.fromtimestamp(trade["timestamp"] / 1000)
            trade_value = trade["value"]
            is_large_order = trade_value >= LARGE_ORDER_THRESHOLD
            
            # 确定时间段
            for period, period_start in time_periods.items():
                if trade_time >= period_start:
                    # 区分主力和散户
                    category = "institutional" if is_large_order else "retail"
                    
                    # 区分流入和流出
                    if trade["side"] == "buy":
                        results[category][period]["inflow"] += trade_value
                    else:
                        results[category][period]["outflow"] += trade_value
        
        # 计算净流入
        for category in ["institutional", "retail"]:
            for period in time_periods:
                inflow = results[category][period]["inflow"]
                outflow = results[category][period]["outflow"]
                results[category][period]["net_flow"] = inflow - outflow
        
        # 确定主导方向
        inst_24h_flow = results["institutional"]["24h"]["net_flow"]
        retail_24h_flow = results["retail"]["24h"]["net_flow"]
        
        if inst_24h_flow > 0 and retail_24h_flow > 0:
            dominant_direction = "强烈看涨"
        elif inst_24h_flow > 0 and retail_24h_flow < 0:
            dominant_direction = "主力看涨，散户看跌"
        elif inst_24h_flow < 0 and retail_24h_flow > 0:
            dominant_direction = "主力看跌，散户看涨"
        elif inst_24h_flow < 0 and retail_24h_flow < 0:
            dominant_direction = "强烈看跌"
        else:
            dominant_direction = "市场中性"
        
        results["dominant_direction"] = dominant_direction
        
        return results
    
    except Exception as e:
        logger.error(f"分析资金流向时出错: {str(e)}")
        raise

async def analyze_whale_activity(symbol, exchange="binance"):
    """分析大户活动"""
    try:
        # 获取最近成交记录
        trades = await get_recent_trades(symbol, 1000, exchange)
        
        # 筛选大单交易
        large_trades = [t for t in trades if t["value"] >= LARGE_ORDER_THRESHOLD]
        
        # 统计买入和卖出
        buy_trades = [t for t in large_trades if t["side"] == "buy"]
        sell_trades = [t for t in large_trades if t["side"] == "sell"]
        
        buy_count = len(buy_trades)
        sell_count = len(sell_trades)
        
        buy_value = sum(t["value"] for t in buy_trades)
        sell_value = sum(t["value"] for t in sell_trades)
        
        net_value = buy_value - sell_value
        
        # 计算大单比例
        total_trades = len(trades)
        large_trade_percentage = (len(large_trades) / total_trades) * 100 if total_trades > 0 else 0
        
        return {
            "symbol": symbol,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "buy_value": buy_value,
            "sell_value": sell_value,
            "net_value": net_value,
            "large_trade_percentage": large_trade_percentage,
            "timestamp": datetime.now().timestamp()
        }
    
    except Exception as e:
        logger.error(f"分析大户活动时出错: {str(e)}")
        raise

async def analyze_order_book_imbalance(symbol, exchange="binance"):
    """分析订单簿不平衡"""
    try:
        # 获取订单簿数据
        order_book = await get_order_book(symbol, 20, exchange)
        
        # 计算买单和卖单总量
        bid_volume = sum(qty for _, qty in order_book["bids"])
        ask_volume = sum(qty for _, qty in order_book["asks"])
        
        total_volume = bid_volume + ask_volume
        
        # 计算买卖比例
        bid_percentage = (bid_volume / total_volume) * 100 if total_volume > 0 else 50
        ask_percentage = (ask_volume / total_volume) * 100 if total_volume > 0 else 50
        
        # 计算不平衡度
        imbalance = bid_percentage - ask_percentage
        
        # 确定市场压力
        if imbalance > 20:
            pressure = "强烈买压"
        elif imbalance > 10:
            pressure = "买压"
        elif imbalance < -20:
            pressure = "强烈卖压"
        elif imbalance < -10:
            pressure = "卖压"
        else:
            pressure = "平衡"
        
        return {
            "symbol": symbol,
            "bid_volume": bid_volume,
            "ask_volume": ask_volume,
            "bid_percentage": bid_percentage,
            "ask_percentage": ask_percentage,
            "imbalance": imbalance,
            "pressure": pressure,
            "timestamp": datetime.now().timestamp()
        }
    
    except Exception as e:
        logger.error(f"分析订单簿不平衡时出错: {str(e)}")
        raise

async def comprehensive_analysis(symbol, exchange="binance"):
    """综合分析"""
    try:
        # 并行获取各项分析结果
        fund_flow_task = analyze_fund_flow(symbol, exchange)
        whale_activity_task = analyze_whale_activity(symbol, exchange)
        order_book_task = analyze_order_book_imbalance(symbol, exchange)
        price_task = get_price(symbol, exchange)
        
        fund_flow, whale_activity, order_book_imbalance, price_data = await asyncio.gather(
            fund_flow_task, whale_activity_task, order_book_task, price_task
        )
        
        # 综合判断市场状态
        inst_flow = fund_flow["institutional"]["24h"]["net_flow"]
        retail_flow = fund_flow["retail"]["24h"]["net_flow"]
        whale_net = whale_activity["net_value"]
        book_imbalance = order_book_imbalance["imbalance"]
        
        # 计算信号分数
        bullish_signals = 0
        bearish_signals = 0
        
        # 主力资金流向信号
        if inst_flow > 0: bullish_signals += 2
        elif inst_flow < 0: bearish_signals += 2
        
        # 散户资金流向信号（反向指标）
        if retail_flow < 0: bullish_signals += 1
        elif retail_flow > 0: bearish_signals += 1
        
        # 大户活动信号
        if whale_net > 0: bullish_signals += 2
        elif whale_net < 0: bearish_signals += 2
        
        # 订单簿不平衡信号
        if book_imbalance > 10: bullish_signals += 1
        elif book_imbalance < -10: bearish_signals += 1
        
        # 确定市场预测
        if bullish_signals - bearish_signals >= 3:
            market_prediction = "强烈看涨"
        elif bullish_signals - bearish_signals >= 1:
            market_prediction = "看涨"
        elif bearish_signals - bullish_signals >= 3:
            market_prediction = "强烈看跌"
        elif bearish_signals - bullish_signals >= 1:
            market_prediction = "看跌"
        else:
            market_prediction = "市场中性"
        
        return {
            "symbol": symbol,
            "price": price_data["price"],
            "change_24h": price_data["change_24h"],
            "fund_flow": fund_flow,
            "whale_activity": whale_activity,
            "order_book_imbalance": order_book_imbalance,
            "market_prediction": market_prediction,
            "bullish_signals": bullish_signals,
            "bearish_signals": bearish_signals,
            "timestamp": datetime.now().timestamp()
        }
    
    except Exception as e:
        logger.error(f"综合分析时出错: {str(e)}")
        raise
