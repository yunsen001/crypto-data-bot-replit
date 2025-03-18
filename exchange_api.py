import os
import aiohttp
import asyncio
import json
from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 交易所API配置
EXCHANGES = {
    "binance": {
        "base_url": "https://api.binance.com",
        "price_endpoint": "/api/v3/ticker/24hr",
        "depth_endpoint": "/api/v3/depth",
        "trades_endpoint": "/api/v3/trades",
    },
    "okx": {
        "base_url": "https://www.okx.com",
        "price_endpoint": "/api/v5/market/ticker",
        "depth_endpoint": "/api/v5/market/books",
        "trades_endpoint": "/api/v5/market/trades",
    },
    "bybit": {
        "base_url": "https://api.bybit.com",
        "price_endpoint": "/v5/market/tickers",
        "depth_endpoint": "/v5/market/orderbook",
        "trades_endpoint": "/v5/market/recent-trade",
    }
}

# 缓存设置
CACHE = {}
CACHE_EXPIRY = 60  # 缓存过期时间（秒）

async def _make_request(url, params=None):
    """发送HTTP请求并返回结果"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"API请求失败: {response.status} - {await response.text()}")
                    return None
    except Exception as e:
        logger.error(f"请求异常: {str(e)}")
        return None

async def get_price(symbol, exchange="binance"):
    """获取指定币种的价格信息"""
    # 检查缓存
    cache_key = f"price_{exchange}_{symbol}"
    if cache_key in CACHE and datetime.now() - CACHE[cache_key]["timestamp"] < timedelta(seconds=CACHE_EXPIRY):
        return CACHE[cache_key]["data"]
    
    # 格式化交易对
    if exchange == "binance":
        formatted_symbol = f"{symbol}USDT"
        params = {"symbol": formatted_symbol}
    elif exchange == "okx":
        formatted_symbol = f"{symbol}-USDT"
        params = {"instId": formatted_symbol}
    elif exchange == "bybit":
        formatted_symbol = f"{symbol}USDT"
        params = {"category": "spot", "symbol": formatted_symbol}
    else:
        raise ValueError(f"不支持的交易所: {exchange}")
    
    # 发送请求
    config = EXCHANGES.get(exchange)
    if not config:
        raise ValueError(f"不支持的交易所: {exchange}")
    
    url = f"{config['base_url']}{config['price_endpoint']}"
    response = await _make_request(url, params)
    
    if not response:
        raise Exception(f"无法从{exchange}获取{symbol}的价格数据")
    
    # 解析响应
    if exchange == "binance":
        price_data = {
            "symbol": symbol,
            "price": float(response["lastPrice"]),
            "change_24h": float(response["priceChangePercent"]),
            "volume_24h": float(response["volume"]),
            "high_24h": float(response["highPrice"]),
            "low_24h": float(response["lowPrice"]),
        }
    elif exchange == "okx":
        data = response["data"][0]
        price_data = {
            "symbol": symbol,
            "price": float(data["last"]),
            "change_24h": float(data["change24h"]) * 100,
            "volume_24h": float(data["vol24h"]),
            "high_24h": float(data["high24h"]),
            "low_24h": float(data["low24h"]),
        }
    elif exchange == "bybit":
        data = response["result"]["list"][0]
        price_data = {
            "symbol": symbol,
            "price": float(data["lastPrice"]),
            "change_24h": float(data["price24hPcnt"]) * 100,
            "volume_24h": float(data["volume24h"]),
            "high_24h": float(data["highPrice24h"]),
            "low_24h": float(data["lowPrice24h"]),
        }
    
    # 更新缓存
    CACHE[cache_key] = {
        "timestamp": datetime.now(),
        "data": price_data
    }
    
    return price_data

async def get_order_book(symbol, limit=20, exchange="binance"):
    """获取订单簿数据"""
    # 检查缓存
    cache_key = f"orderbook_{exchange}_{symbol}_{limit}"
    if cache_key in CACHE and datetime.now() - CACHE[cache_key]["timestamp"] < timedelta(seconds=CACHE_EXPIRY):
        return CACHE[cache_key]["data"]
    
    # 格式化交易对和参数
    if exchange == "binance":
        formatted_symbol = f"{symbol}USDT"
        params = {"symbol": formatted_symbol, "limit": limit}
    elif exchange == "okx":
        formatted_symbol = f"{symbol}-USDT"
        params = {"instId": formatted_symbol, "sz": limit}
    elif exchange == "bybit":
        formatted_symbol = f"{symbol}USDT"
        params = {"category": "spot", "symbol": formatted_symbol, "limit": limit}
    else:
        raise ValueError(f"不支持的交易所: {exchange}")
    
    # 发送请求
    config = EXCHANGES.get(exchange)
    if not config:
        raise ValueError(f"不支持的交易所: {exchange}")
    
    url = f"{config['base_url']}{config['depth_endpoint']}"
    response = await _make_request(url, params)
    
    if not response:
        raise Exception(f"无法从{exchange}获取{symbol}的订单簿数据")
    
    # 解析响应
    if exchange == "binance":
        order_book = {
            "symbol": symbol,
            "bids": [[float(price), float(qty)] for price, qty in response["bids"]],
            "asks": [[float(price), float(qty)] for price, qty in response["asks"]],
            "timestamp": response["lastUpdateId"]
        }
    elif exchange == "okx":
        data = response["data"][0]
        order_book = {
            "symbol": symbol,
            "bids": [[float(item[0]), float(item[1])] for item in data["bids"]],
            "asks": [[float(item[0]), float(item[1])] for item in data["asks"]],
            "timestamp": int(data["ts"])
        }
    elif exchange == "bybit":
        data = response["result"]
        order_book = {
            "symbol": symbol,
            "bids": [[float(item[0]), float(item[1])] for item in data["b"]],
            "asks": [[float(item[0]), float(item[1])] for item in data["a"]],
            "timestamp": int(data["ts"])
        }
    
    # 更新缓存
    CACHE[cache_key] = {
        "timestamp": datetime.now(),
        "data": order_book
    }
    
    return order_book

async def get_recent_trades(symbol, limit=100, exchange="binance"):
    """获取最近成交记录"""
    # 检查缓存
    cache_key = f"trades_{exchange}_{symbol}_{limit}"
    if cache_key in CACHE and datetime.now() - CACHE[cache_key]["timestamp"] < timedelta(seconds=CACHE_EXPIRY):
        return CACHE[cache_key]["data"]
    
    # 格式化交易对和参数
    if exchange == "binance":
        formatted_symbol = f"{symbol}USDT"
        params = {"symbol": formatted_symbol, "limit": limit}
    elif exchange == "okx":
        formatted_symbol = f"{symbol}-USDT"
        params = {"instId": formatted_symbol, "limit": limit}
    elif exchange == "bybit":
        formatted_symbol = f"{symbol}USDT"
        params = {"category": "spot", "symbol": formatted_symbol, "limit": limit}
    else:
        raise ValueError(f"不支持的交易所: {exchange}")
    
    # 发送请求
    config = EXCHANGES.get(exchange)
    if not config:
        raise ValueError(f"不支持的交易所: {exchange}")
    
    url = f"{config['base_url']}{config['trades_endpoint']}"
    response = await _make_request(url, params)
    
    if not response:
        raise Exception(f"无法从{exchange}获取{symbol}的成交记录")
    
    # 解析响应
    trades = []
    if exchange == "binance":
        for trade in response:
            trades.append({
                "id": trade["id"],
                "price": float(trade["price"]),
                "amount": float(trade["qty"]),
                "value": float(trade["price"]) * float(trade["qty"]),
                "side": "buy" if trade["isBuyerMaker"] else "sell",
                "timestamp": trade["time"]
            })
    elif exchange == "okx":
        for trade in response["data"]:
            trades.append({
                "id": trade["tradeId"],
                "price": float(trade["px"]),
                "amount": float(trade["sz"]),
                "value": float(trade["px"]) * float(trade["sz"]),
                "side": "sell" if trade["side"] == "buy" else "buy",  # OKX的side是taker的方向
                "timestamp": int(trade["ts"])
            })
    elif exchange == "bybit":
        for trade in response["result"]["list"]:
            trades.append({
                "id": trade["i"],
                "price": float(trade["p"]),
                "amount": float(trade["v"]),
                "value": float(trade["p"]) * float(trade["v"]),
                "side": "buy" if trade["S"] == "Buy" else "sell",
                "timestamp": int(trade["T"])
            })
    
    # 更新缓存
    CACHE[cache_key] = {
        "timestamp": datetime.now(),
        "data": trades
    }
    
    return trades

# 多交易所数据聚合
async def get_aggregated_price(symbol):
    """获取多个交易所的聚合价格"""
    tasks = []
    for exchange in EXCHANGES.keys():
        tasks.append(get_price(symbol, exchange))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_results = [r for r in results if not isinstance(r, Exception) and r is not None]
    
    if not valid_results:
        raise Exception(f"无法从任何交易所获取{symbol}的价格数据")
    
    # 计算平均价格
    avg_price = sum(r["price"] for r in valid_results) / len(valid_results)
    
    return {
        "symbol": symbol,
        "price": avg_price,
        "exchange_prices": {ex: r["price"] for ex, r in zip(EXCHANGES.keys(), results) if not isinstance(r, Exception) and r is not None},
        "timestamp": datetime.now().timestamp()
    }
