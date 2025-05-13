import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

# 載入環境變數
load_dotenv()

class Config:
    """應用程式配置類"""
    # 數據庫配置
    DB_HOST = os.getenv('DB_HOST')
    DB_NAME = os.getenv('DB_NAME')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_DRIVER = os.getenv('DB_DRIVER')
    
    # 安全配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    
    # CORS 配置
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
    
    # 其他配置
    DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
    PORT = int(os.getenv('PORT', 3001))

def create_app(test_config=None):
    """創建並配置應用程式實例"""
    app = Flask(__name__)
    
    # 配置應用
    if test_config is None:
        # 載入實例配置
        app.config.from_object(Config)
    else:
        # 載入測試配置
        app.config.from_mapping(test_config)
    
    # 暫時禁用 CORS 以避免測試中的錯誤
    # CORS(app, resources={r"/api/*": {
    #     "origins": ["http://localhost", "http://localhost:3000"],
    #     "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    # }})
    
    # 確保實例文件夾存在
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass
    
    return app
