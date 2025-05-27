import os
from dotenv import load_dotenv
from flask import Flask, request # Flask 實例化移到 create_app 中
from flask_cors import CORS

# 載入環境變數
# 確保 .env 檔案與此 config.py 在同一目錄，或者 load_dotenv() 指定路徑
load_dotenv()

class Config:
    """應用程式配置類"""
    # 資料庫配置
    DB_HOST = os.getenv('DB_HOST')
    DB_NAME = os.getenv('DB_NAME')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_DRIVER = os.getenv('DB_DRIVER')
    # 新增：控制是否信任資料庫伺服器憑證
    DB_TRUST_SERVER_CERTIFICATE = os.getenv('DB_TRUST_SERVER_CERTIFICATE', 'no').lower() == 'yes'
    
    # 安全配置
    # 修改後的 SECRET_KEY 預設值，更明確提示需要更改
    # 實際的密鑰應從環境變數 SECRET_KEY 讀取
    SECRET_KEY = os.getenv('SECRET_KEY') # 移除預設值，強制從環境變數讀取
                                        # 或者保留一個非常明確的警告性預設值，並在應用啟動時檢查
    # SECRET_KEY = os.getenv('SECRET_KEY', '!!DEFAULT_KEY_MUST_BE_CHANGED_IN_PRODUCTION_ENV_VARIABLE!!')


    # CORS 配置
    # 從環境變數讀取 CORS_ORIGINS，預設為 'http://localhost:3000' (適合開發)
    # 生產環境應設定為實際的前端來源
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')
    
    # 其他配置
    # DEBUG 模式預設為 False，除非環境變數明確設為 True
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() in ('true', '1', 't') \
            or os.getenv('FLASK_ENV', 'production').lower() == 'development'
            
    PORT = int(os.getenv('PORT', 5000)) # Flask 常用的預設 PORT 是 5000

    # 應用程式根日誌級別 (可選，用於更細緻的日誌控制)
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

    # 環境設定
    ENV = os.getenv('FLASK_ENV', 'production')


def create_app(test_config=None):
    """創建並配置應用程式實例的工廠函數"""
    app = Flask(__name__) # 應用實例在工廠函數內部創建
    
    # 配置應用
    if test_config is None:
        # 載入實例配置 (Config 類)
        app.config.from_object(Config)
    else:
        # 載入測試配置 (如果傳入)
        app.config.from_mapping(test_config)

    # --- 關鍵安全檢查：SECRET_KEY ---
    # 必須在應用啟動時檢查 SECRET_KEY 是否已安全設定
    if not app.config.get('SECRET_KEY') or \
       app.config.get('SECRET_KEY') == '!!DEFAULT_KEY_MUST_BE_CHANGED_IN_PRODUCTION_ENV_VARIABLE!!' or \
       app.config.get('SECRET_KEY') == 'changeme_in_production_to_a_strong_random_secret_key': # 檢查 .env 中的開發預設值
        app.logger.critical(
            "CRITICAL SECURITY WARNING: SECRET_KEY is not set or is using an insecure default value. "
            "This application is NOT secure for production. "
            "Please set a strong, random SECRET_KEY environment variable."
        )
        # 在生產環境中，如果 SECRET_KEY 不安全，應考慮是否要阻止應用程式啟動
        # Fix for KeyError: 'ENV' - use get with default and check environment directly
        if os.getenv('FLASK_ENV', 'production').lower() == 'production':
             raise ValueError(
                 "Refusing to start in production with an insecure SECRET_KEY. "
                 "Set a proper SECRET_KEY environment variable."
            )
    
    # 設定日誌級別 (可選)
    # import logging
    # app.logger.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))
    # if app.debug: # 開發模式下可能有更詳細的日誌
    #    app.logger.setLevel(logging.DEBUG)


    # 設定 CORS
    # 確保 app.config['CORS_ORIGINS'] 是正確的列表
    cors_origins_config = app.config.get('CORS_ORIGINS', [])
    if isinstance(cors_origins_config, str): # 以防萬一配置中仍是字串
        cors_origins_config = [origin.strip() for origin in cors_origins_config.split(',')]
    
    CORS(app,  
         resources={r"/api/*": {"origins": cors_origins_config}},
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization", "X-Requested-With"],  # 添加常用的請求頭
         expose_headers=["Content-Type", "Authorization"]
    )
    
    # 添加調試日誌
    app.logger.info(f"CORS configured for origins: {cors_origins_config}")
    app.logger.info(f"Server running on port: {app.config.get('PORT', 5000)}")

    # 添加一個簡單的測試路由來驗證 CORS
    @app.route('/api/test', methods=['GET', 'OPTIONS'])
    def test_cors():
        from flask import request, jsonify
        return jsonify({'message': 'CORS test successful', 'origin': request.headers.get('Origin')})

    

    # 確保實例文件夾存在 (如果使用 instance-relative config)
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        app.logger.error(f"Could not create instance path: {app.instance_path}")
        pass # 或者根據情況處理此錯誤
    
    # 在這裡初始化擴展 (如資料庫) 和註冊藍圖
    # 例如: from . import db
    # db.init_app(app)
    #
    # from .routes import auth_bp, form_bp
    # app.register_blueprint(auth_bp)
    # app.register_blueprint(form_bp)

    return app