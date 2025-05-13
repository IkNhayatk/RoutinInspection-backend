from config import create_app
from db import init_app
# 直接從各自的模組導入藍圖
from routes.auth_routes import auth_bp
from routes.form_routes import form_bp
# flask_cors 的 CORS 實例化已移至 config.py 中的 create_app
 
def create_application(test_config=None):
    """創建並配置 Flask 應用實例，可選擇測試配置"""
    # 創建應用，傳遞測試配置（如果有）
    app = create_app(test_config)
    
    # CORS 已在 create_app 中根據設定檔進行配置
    # 不再需要此處的 CORS(app, ...)
    
    # 初始化數據庫
    init_app(app)
    
    # 註冊藍圖
    app.register_blueprint(auth_bp)
    app.register_blueprint(form_bp)
     
    # 新增測試路由
    @app.route('/api/ping', methods=['GET'])
    def ping():
        return {"success": True, "message": "RoutinInspection API 服務正常運行"}
    
    return app

# 創建應用實例
app = create_application()

if __name__ == '__main__':
    # 使用設定檔中的 PORT 和 DEBUG 設定
    # 將 host 設為 '0.0.0.0' 以允許來自其他機器的連接（開發時常用）
    app.run(host='0.0.0.0', port=app.config['PORT'], debug=app.config['DEBUG'])
