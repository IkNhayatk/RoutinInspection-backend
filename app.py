# 導入 create_app 工廠函數
from config import create_app
# 導入資料庫初始化函數
from db import init_app as init_db_connections # 給 init_app 一個更明確的名稱
import os  # Add missing import for os.getenv

# 從各自的模組導入藍圖
from routes.auth_routes import auth_bp
from routes.form_routes import form_bp
from routes.route_routes import route_bp
 
def register_blueprints(app):
    """輔助函數：註冊所有藍圖"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(form_bp)
    app.register_blueprint(route_bp)
    app.logger.info("Blueprints registered.")

def setup_basic_routes(app):
    """輔助函數：設定一些基本的非藍圖路由"""
    @app.route('/api/ping', methods=['GET'])
    def ping():
        return {"success": True, "message": "RoutinInspection API 服務正常運行 (v2)"}
    app.logger.info("Basic /api/ping route registered.")


# 除錯：確認環境變數載入狀況
print("=== DEBUG INFO ===")
print(f"Current working directory: {os.getcwd()}")
print(f"SECRET_KEY exists: {bool(os.getenv('SECRET_KEY'))}")
print(f"CORS_ORIGINS: {os.getenv('CORS_ORIGINS')}")
print(f"FLASK_ENV: {os.getenv('FLASK_ENV')}")

# 使用工廠函數創建應用實例
# 這允許更靈活的配置，例如為測試創建不同的應用實例
app = create_app()

# 在應用程式上下文中初始化資料庫連接等
# init_db_connections (來自 db.py) 會設定 teardown_appcontext(close_db)
# 和執行 db.py 中的 init_db(app) 函數 (您需要確定 init_db 的具體作用)
init_db_connections(app) # 初始化資料庫相關設置

# 註冊藍圖
register_blueprints(app)

# 設定基礎路由
setup_basic_routes(app)

# 應用程式的運行部分
if __name__ == '__main__':
    # 使用來自 app.config 的 PORT 和 DEBUG 設定
    # host='0.0.0.0' 允許來自外部的連接，適合容器化或開發時從其他機器訪問
    # 生產環境應使用 WSGI 伺服器 (如 Gunicorn) 而不是 Flask 內建的開發伺服器
    print(f"App CORS_ORIGINS: {app.config.get('CORS_ORIGINS')}")
    print(f"App SECRET_KEY exists: {bool(app.config.get('SECRET_KEY'))}")
    print("=== Starting Flask ===")
    
    # 從配置獲取 host, port, debug
    # DEBUG 通常由 FLASK_DEBUG 或 FLASK_ENV 控制，並在 create_app 時設定到 app.config['DEBUG']
    # PORT 也在 config.py 中設定
    host = os.getenv('HOST', '0.0.0.0') # 也可以從環境變數獲取 HOST
    port = app.config.get('PORT', 3001) # 從 app.config 獲取 PORT
    debug_mode = app.config.get('DEBUG', False) # 從 app.config 獲取 DEBUG 狀態

    app.logger.info(f"Starting Flask development server on {host}:{port} with DEBUG={debug_mode}")
    app.run(host=host, port=port, debug=debug_mode, use_reloader=debug_mode)