import os
import logging
from dotenv import load_dotenv
from bot_core import CryptoBot
from flask import Flask, request, Response

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 获取环境变量
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
USE_WEBHOOK = os.environ.get("USE_WEBHOOK", "false").lower() == "true"

# 创建Flask应用
app = Flask(__name__)

# 创建机器人实例
bot = None

@app.route('/webhook', methods=['POST'])
def webhook():
    """处理webhook请求"""
    global bot
    if bot is None:
        bot = CryptoBot(BOT_TOKEN)
        
    if request.headers.get('content-type') == 'application/json':
        update = request.get_json()
        bot.process_update(update)
        return Response('ok', status=200)
    else:
        return Response('error', status=403)

@app.route('/')
def index():
    """主页"""
    return 'Crypto Fund Data Bot is running'

@app.route('/set_webhook')
def set_webhook():
    """设置webhook"""
    global bot
    if bot is None:
        bot = CryptoBot(BOT_TOKEN)
        
    success = bot.set_webhook(WEBHOOK_URL)
    if success:
        return 'Webhook setup successful'
    else:
        return 'Webhook setup failed'

# 如果直接运行此文件
if __name__ == "__main__":
    if USE_WEBHOOK and WEBHOOK_URL:
        logger.info(f"使用webhook模式启动机器人，webhook URL: {WEBHOOK_URL}")
        # 创建机器人实例
        bot = CryptoBot(BOT_TOKEN)
        # 设置webhook
        bot.set_webhook(WEBHOOK_URL)
        # 启动Flask应用
        app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8443)))
    else:
        logger.info("使用轮询模式启动机器人")
        bot = CryptoBot(BOT_TOKEN)
        bot.run_polling()
