# PythonAnywhere平台特定配置文件
# 这个文件用于设置PythonAnywhere的WSGI配置

import os
import sys

# 添加项目目录到路径
path = '/home/yourusername/crypto_bot'
if path not in sys.path:
    sys.path.append(path)

# 导入Flask应用
from main import app as application
