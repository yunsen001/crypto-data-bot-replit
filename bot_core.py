import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# 导入其他模块
from exchange_api import get_price, get_aggregated_price
from data_analysis import analyze_fund_flow, analyze_whale_activity, comprehensive_analysis
from user_interface import UserInterface

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class CryptoBot:
    def __init__(self, token):
        self.token = token
        self.application = Application.builder().token(token).build()
        self._register_handlers()
        
    def _register_handlers(self):
        """注册命令处理器"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("price", self.price_command))
        self.application.add_handler(CommandHandler("flow", self.flow_command))
        self.application.add_handler(CommandHandler("whale", self.whale_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理/start命令"""
        await update.message.reply_text('欢迎使用加密货币资金数据机器人！发送 /help 查看可用命令。')
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理/help命令"""
        help_text = """
可用命令列表：
/price [币种] - 查询当前价格
/flow [币种] - 查询资金流向
/whale [币种] - 查询大户活动
/help - 显示此帮助信息
        """
        await update.message.reply_text(help_text)
        
    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理/price命令"""
        if not context.args:
            await update.message.reply_text("请指定币种，例如：/price BTC")
            return
            
        symbol = context.args[0].upper()
        # 调用数据获取模块获取价格
        try:
            price_data = await get_price(symbol)
            message, reply_markup = await UserInterface.format_price_message(price_data)
            await update.message.reply_text(message, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"获取{symbol}价格时出错: {str(e)}")
            await update.message.reply_text(f"获取{symbol}价格时出错: {str(e)}")
    
    async def flow_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理/flow命令"""
        if not context.args:
            await update.message.reply_text("请指定币种，例如：/flow BTC")
            return
            
        symbol = context.args[0].upper()
        # 调用数据分析模块获取资金流向
        try:
            flow_data = await analyze_fund_flow(symbol)
            message, reply_markup, chart = await UserInterface.format_fund_flow_message(flow_data)
            
            if chart:
                await update.message.reply_photo(chart, caption=message, reply_markup=reply_markup)
            else:
                await update.message.reply_text(message, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"分析{symbol}资金流向时出错: {str(e)}")
            await update.message.reply_text(f"分析{symbol}资金流向时出错: {str(e)}")
    
    async def whale_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理/whale命令"""
        if not context.args:
            await update.message.reply_text("请指定币种，例如：/whale BTC")
            return
            
        symbol = context.args[0].upper()
        # 调用数据分析模块获取大户活动
        try:
            whale_data = await analyze_whale_activity(symbol)
            message, reply_markup, chart = await UserInterface.format_whale_activity_message(whale_data)
            
            if chart:
                await update.message.reply_photo(chart, caption=message, reply_markup=reply_markup)
            else:
                await update.message.reply_text(message, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"分析{symbol}大户活动时出错: {str(e)}")
            await update.message.reply_text(f"分析{symbol}大户活动时出错: {str(e)}")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理按钮回调"""
        query = update.callback_query
        await query.answer()
        
        # 解析回调数据
        data = query.data
        parts = data.split('_')
        action = parts[0]
        symbol = parts[1]
        
        try:
            if action == "price":
                price_data = await get_price(symbol)
                message, reply_markup = await UserInterface.format_price_message(price_data)
                await query.edit_message_text(message, reply_markup=reply_markup)
                
            elif action == "flow":
                flow_data = await analyze_fund_flow(symbol)
                message, reply_markup, _ = await UserInterface.format_fund_flow_message(flow_data)
                await query.edit_message_text(message, reply_markup=reply_markup)
                
            elif action == "whale":
                whale_data = await analyze_whale_activity(symbol)
                message, reply_markup, _ = await UserInterface.format_whale_activity_message(whale_data)
                await query.edit_message_text(message, reply_markup=reply_markup)
                
            elif action == "analyze":
                analysis_data = await comprehensive_analysis(symbol)
                message, reply_markup, _ = await UserInterface.format_comprehensive_analysis(analysis_data)
                await query.edit_message_text(message, reply_markup=reply_markup)
                
        except Exception as e:
            logger.error(f"处理按钮回调时出错: {str(e)}")
            await query.edit_message_text(f"处理请求时出错: {str(e)}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理普通文本消息"""
        text = update.message.text
        await update.message.reply_text(f"我不理解这个命令。发送 /help 查看可用命令。")
    
    def run_polling(self):
        """使用轮询方式运行机器人"""
        self.application.run_polling()
    
    def set_webhook(self, webhook_url):
        """设置webhook"""
        try:
            self.application.bot.set_webhook(webhook_url)
            return True
        except Exception as e:
            logger.error(f"设置webhook时出错: {str(e)}")
            return False
    
    def process_update(self, update_data):
        """处理webhook更新"""
        self.application.process_update(Update.de_json(update_data, self.application.bot))
