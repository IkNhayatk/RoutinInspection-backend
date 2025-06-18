import os
from dotenv import load_dotenv
from flask import Flask, request # Flask 實例化移到 create_app 中
from flask_cors import CORS

def _get_bool_env(env_var, default=False):
    """Helper function to parse boolean environment variables"""
    value = os.getenv(env_var, '').lower()
    if default:
        return value not in ('false', 'f', '0', 'no', 'n', '')
    else:
        return value in ('true', 't', '1', 'yes', 'y')

def _get_int_env(env_var, default=None):
    """Helper function to parse integer environment variables"""
    try:
        return int(os.getenv(env_var, default))
    except (ValueError, TypeError):
        return default

class Config:
    """應用程式配置類"""
    def __init__(self, load_env=True):
        # Load environment variables only when Config is instantiated
        # This allows tests to properly mock environment variables
        # load_env parameter allows tests to skip .env loading
        if load_env:
            load_dotenv()
        
        # 資料庫配置
        self.DB_HOST = os.getenv('DB_HOST')
        self.DB_NAME = os.getenv('DB_NAME')
        self.DB_USER = os.getenv('DB_USER')
        self.DB_PASSWORD = os.getenv('DB_PASSWORD')
        self.DB_DRIVER = os.getenv('DB_DRIVER')
        # 新增：控制是否信任資料庫伺服器憑證
        self.DB_TRUST_SERVER_CERTIFICATE = _get_bool_env('DB_TRUST_SERVER_CERTIFICATE', False)
        
        # 安全配置
        self.SECRET_KEY = os.getenv('SECRET_KEY', '!!DEFAULT_KEY_MUST_BE_CHANGED_IN_PRODUCTION_ENV_VARIABLE!!')

        # CORS 配置
        cors_origins_str = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000')
        self.CORS_ORIGINS = [origin.strip() for origin in cors_origins_str.split(',') if origin.strip()]
        
        # 其他配置
        # 環境設定 - 必須先設定才能用於 DEBUG 判斷
        self.ENV = os.getenv('FLASK_ENV', 'production')
        
        # DEBUG 模式預設為 False，只有在明確設定或開發環境才啟用
        flask_debug = _get_bool_env('FLASK_DEBUG', False)
        is_development = self.ENV.lower() == 'development'
        self.DEBUG = flask_debug or is_development
                
        self.PORT = _get_int_env('PORT', 3001)

        # 應用程式根日誌級別 (可選，用於更細緻的日誌控制)
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()


def create_app(test_config=None, load_env=True):
    """創建並配置應用程式實例的工廠函數"""
    app = Flask(__name__) # 應用實例在工廠函數內部創建
    
    # 配置應用
    if test_config is None:
        # 載入實例配置 (Config 類)
        config_instance = Config(load_env=load_env)
        app.config.from_object(config_instance)
    else:
        # 載入測試配置 (如果傳入)
        # First load default config, then override with test config
        config_instance = Config(load_env=load_env)
        app.config.from_object(config_instance)
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
    app.logger.info(f"Server running on port: {app.config.get('PORT', 3001)}")

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
    
    # 移除 blueprint 註冊 - 這將在 app.py 中統一處理
    # 原本的 blueprint 註冊代碼已移除

    return app