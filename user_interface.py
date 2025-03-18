from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import matplotlib.pyplot as plt
import io
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserInterface:
    @staticmethod
    async def format_price_message(price_data):
        """格式化价格消息"""
        message = f"💰 {price_data['symbol']}/USDT 价格信息\n\n"
        message += f"当前价格: ${price_data['price']:,.2f}\n"
        message += f"24小时变化: {price_data['change_24h']:+.2f}%\n"
        message += f"24小时成交量: ${price_data['volume_24h']:,.2f}\n"
        message += f"24小时最高: ${price_data['high_24h']:,.2f}\n"
        message += f"24小时最低: ${price_data['low_24h']:,.2f}\n\n"
        message += f"🕒 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 创建内联键盘
        keyboard = [
            [
                InlineKeyboardButton("📊 资金流向", callback_data=f"flow_{price_data['symbol']}"),
                InlineKeyboardButton("🐋 大户活动", callback_data=f"whale_{price_data['symbol']}")
            ],
            [
                InlineKeyboardButton("📈 综合分析", callback_data=f"analyze_{price_data['symbol']}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        return message, reply_markup
    
    @staticmethod
    async def format_fund_flow_message(flow_data):
        """格式化资金流向消息"""
        symbol = flow_data["symbol"]
        
        message = f"💹 {symbol}/USDT 资金流向分析\n\n"
        
        # 添加各时间段数据
        message += "⏰ 时间段资金净流入/流出：\n"
        for period in ["15m", "1h", "4h", "24h"]:
            inst_flow = flow_data["institutional"][period]["net_flow"]
            retail_flow = flow_data["retail"][period]["net_flow"]
            
            inst_flow_str = f"${inst_flow:+,.2f}" if inst_flow >= 0 else f"${inst_flow:,.2f}"
            retail_flow_str = f"${retail_flow:+,.2f}" if retail_flow >= 0 else f"${retail_flow:,.2f}"
            
            if period == "15m":
                period_str = "15分钟"
            elif period == "1h":
                period_str = "1小时"
            elif period == "4h":
                period_str = "4小时"
            else:
                period_str = "24小时"
            
            message += f"• {period_str}：主力 {inst_flow_str} | 散户 {retail_flow_str}\n"
        
        message += f"\n🔍 主导方向：{flow_data['dominant_direction']}\n"
        
        # 计算主力和散户占比
        inst_24h = abs(flow_data["institutional"]["24h"]["net_flow"])
        retail_24h = abs(flow_data["retail"]["24h"]["net_flow"])
        total = inst_24h + retail_24h
        
        if total > 0:
            inst_percentage = (inst_24h / total) * 100
            retail_percentage = (retail_24h / total) * 100
            message += f"主力占比：{inst_percentage:.1f}%\n"
            message += f"散户占比：{retail_percentage:.1f}%\n\n"
        
        message += f"🕒 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 创建内联键盘
        keyboard = [
            [
                InlineKeyboardButton("💰 价格信息", callback_data=f"price_{symbol}"),
                InlineKeyboardButton("🐋 大户活动", callback_data=f"whale_{symbol}")
            ],
            [
                InlineKeyboardButton("📈 综合分析", callback_data=f"analyze_{symbol}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # 创建资金流向图表
        try:
            buffer = io.BytesIO()
            plt.figure(figsize=(10, 6))
            
            # 准备数据
            periods = ["15m", "1h", "4h", "24h"]
            inst_flows = [flow_data["institutional"][p]["net_flow"] for p in periods]
            retail_flows = [flow_data["retail"][p]["net_flow"] for p in periods]
            
            # 绘制柱状图
            x = range(len(periods))
            width = 0.35
            
            plt.bar([i - width/2 for i in x], inst_flows, width, label='主力机构')
            plt.bar([i + width/2 for i in x], retail_flows, width, label='散户')
            
            plt.xlabel('时间段')
            plt.ylabel('资金净流入/流出 (USD)')
            plt.title(f'{symbol}/USDT 资金流向分析')
            plt.xticks(x, ["15分钟", "1小时", "4小时", "24小时"])
            plt.axhline(y=0, color='r', linestyle='-', alpha=0.3)
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            
            return message, reply_markup, buffer
        except Exception as e:
            logger.error(f"创建图表时出错: {str(e)}")
            return message, reply_markup, None
    
    @staticmethod
    async def format_whale_activity_message(whale_data):
        """格式化大户活动消息"""
        symbol = whale_data["symbol"]
        
        message = f"🐋 {symbol}/USDT 大户活动分析\n\n"
        
        buy_value = whale_data["buy_value"]
        sell_value = whale_data["sell_value"]
        net_value = whale_data["net_value"]
        
        message += f"大单买入: {whale_data['buy_count']}笔，总额${buy_value:,.2f}\n"
        message += f"大单卖出: {whale_data['sell_count']}笔，总额${sell_value:,.2f}\n"
        
        if net_value >= 0:
            message += f"净流入: ${net_value:+,.2f} 📈\n"
        else:
            message += f"净流出: ${net_value:,.2f} 📉\n"
        
        message += f"\n大单交易占比: {whale_data['large_trade_percentage']:.2f}%\n"
        
        # 判断大户情绪
        if net_value > 0 and whale_data['buy_count'] > whale_data['sell_count']:
            sentiment = "积极买入"
        elif net_value > 0 and whale_data['buy_count'] <= whale_data['sell_count']:
            sentiment = "大额买入"
        elif net_value < 0 and whale_data['sell_count'] > whale_data['buy_count']:
            sentiment = "积极卖出"
        elif net_value < 0 and whale_data['sell_count'] <= whale_data['buy_count']:
            sentiment = "大额卖出"
        else:
            sentiment = "中性"
        
        message += f"大户情绪: {sentiment}\n\n"
        message += f"🕒 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 创建内联键盘
        keyboard = [
            [
                InlineKeyboardButton("💰 价格信息", callback_data=f"price_{symbol}"),
                InlineKeyboardButton("📊 资金流向", callback_data=f"flow_{symbol}")
            ],
            [
                InlineKeyboardButton("📈 综合分析", callback_data=f"analyze_{symbol}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # 创建大户活动图表
        try:
            buffer = io.BytesIO()
            plt.figure(figsize=(10, 6))
            
            # 绘制饼图
            labels = ['大单买入', '大单卖出']
            sizes = [buy_value, sell_value]
            colors = ['lightgreen', 'lightcoral']
            explode = (0.1, 0)  # 突出买入部分
            
            plt.pie(sizes, explode=explode, labels=labels, colors=colors,
                    autopct='%1.1f%%', shadow=True, startangle=90)
            plt.axis('equal')  # 确保饼图是圆的
            plt.title(f'{symbol}/USDT 大户交易分布')
            
            plt.tight_layout()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            
            return message, reply_markup, buffer
        except Exception as e:
            logger.error(f"创建图表时出错: {str(e)}")
            return message, reply_markup, None
    
    @staticmethod
    async def format_comprehensive_analysis(analysis_data):
        """格式化综合分析消息"""
        symbol = analysis_data["symbol"]
        
        message = f"📊 {symbol}/USDT 综合市场分析\n\n"
        
        # 基本价格信息
        message += f"当前价格: ${analysis_data['price']:,.2f}\n"
        message += f"24小时变化: {analysis_data['change_24h']:+.2f}%\n\n"
        
        # 资金流向摘要
        inst_24h = analysis_data["fund_flow"]["institutional"]["24h"]["net_flow"]
        retail_24h = analysis_data["fund_flow"]["retail"]["24h"]["net_flow"]
        
        inst_flow_str = f"${inst_24h:+,.2f}" if inst_24h >= 0 else f"${inst_24h:,.2f}"
        retail_flow_str = f"${retail_24h:+,.2f}" if retail_24h >= 0 else f"${retail_24h:,.2f}"
        
        message += "💹 资金流向 (24h):\n"
        message += f"• 主力: {inst_flow_str}\n"
        message += f"• 散户: {retail_flow_str}\n\n"
        
        # 大户活动摘要
        whale_net = analysis_data["whale_activity"]["net_value"]
        whale_net_str = f"${whale_net:+,.2f}" if whale_net >= 0 else f"${whale_net:,.2f}"
        
        message += "🐋 大户活动:\n"
        message += f"• 大单净流入: {whale_net_str}\n"
        message += f"• 大单占比: {analysis_data['whale_activity']['large_trade_percentage']:.2f}%\n\n"
        
        # 订单簿分析
        imbalance = analysis_data["order_book_imbalance"]["imbalance"]
        pressure = analysis_data["order_book_imbalance"]["pressure"]
        
        message += "📚 订单簿分析:\n"
        message += f"• 买卖不平衡度: {imbalance:+.2f}%\n"
        message += f"• 市场压力: {pressure}\n\n"
        
        # 市场预测
        message += f"🔮 市场预测: {analysis_data['market_prediction']}\n"
        message += f"• 看涨信号: {analysis_data['bullish_signals']}\n"
        message += f"• 看跌信号: {analysis_data['bearish_signals']}\n\n"
        
        message += f"🕒 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 创建内联键盘
        keyboard = [
            [
                InlineKeyboardButton("💰 价格信息", callback_data=f"price_{symbol}"),
                InlineKeyboardButton("📊 资金流向", callback_data=f"flow_{symbol}")
            ],
            [
                InlineKeyboardButton("🐋 大户活动", callback_data=f"whale_{symbol}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # 创建综合分析图表
        try:
            buffer = io.BytesIO()
            plt.figure(figsize=(10, 8))
            
            # 创建子图
            plt.subplot(2, 1, 1)
            
            # 资金流向柱状图
            periods = ["15m", "1h", "4h", "24h"]
            inst_flows = [analysis_data["fund_flow"]["institutional"][p]["net_flow"] for p in periods]
            retail_flows = [analysis_data["fund_flow"]["retail"][p]["net_flow"] for p in periods]
            
            x = range(len(periods))
            width = 0.35
            
            plt.bar([i - width/2 for i in x], inst_flows, width, label='主力机构')
            plt.bar([i + width/2 for i in x], retail_flows, width, label='散户')
            
            plt.xlabel('时间段')
            plt.ylabel('资金净流入/流出 (USD)')
            plt.title(f'{symbol}/USDT 资金流向分析')
            plt.xticks(x, ["15分钟", "1小时", "4小时", "24小时"])
            plt.axhline(y=0, color='r', linestyle='-', alpha=0.3)
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # 信号强度图
            plt.subplot(2, 1, 2)
            
            categories = ['主力资金', '散户资金', '大户活动', '订单簿', '总体']
            
            # 计算各类别的信号强度（-5到+5的范围）
            signals = []
            
            # 主力资金信号
            if inst_24h > 0:
                inst_signal = min(5, inst_24h / 100000)  # 根据资金量缩放
            else:
                inst_signal = max(-5, inst_24h / 100000)
            signals.append(inst_signal)
            
            # 散户资金信号（反向指标）
            if retail_24h < 0:
                retail_signal = min(5, abs(retail_24h) / 50000)
            else:
                retail_signal = max(-5, -retail_24h / 50000)
            signals.append(retail_signal)
            
            # 大户活动信号
            if whale_net > 0:
                whale_signal = min(5, whale_net / 100000)
            else:
                whale_signal = max(-5, whale_net / 100000)
            signals.append(whale_signal)
            
            # 订单簿信号
            book_signal = max(-5, min(5, imbalance / 4))
            signals.append(book_signal)
            
            # 总体信号
            overall_signal = (analysis_data['bullish_signals'] - analysis_data['bearish_signals']) / 2
            signals.append(overall_signal)
            
            # 绘制水平条形图
            colors = ['green' if s > 0 else 'red' for s in signals]
            plt.barh(categories, signals, color=colors)
            plt.axvline(x=0, color='black', linestyle='-')
            plt.xlim(-5, 5)
            plt.xlabel('看跌 ←→ 看涨')
            plt.title('市场信号强度')
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            
            return message, reply_markup, buffer
        except Exception as e:
            logger.error(f"创建图表时出错: {str(e)}")
            return message, reply_markup, None
