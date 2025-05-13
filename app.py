from config import create_app
from db import init_app
# 直接從各自的模組導入藍圖
from routes.auth_routes import auth_bp
from routes.form_routes import form_bp
from flask_cors import CORS  # 導入 CORS
 
def create_application(test_config=None):
    """創建並配置 Flask 應用實例，可選擇測試配置"""
    # 創建應用，傳遞測試配置（如果有）
    app = create_app(test_config)
    
    # 啟用 CORS，允許前端應用訪問 API
    CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})
    
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
    app.run(port=3001, debug=True)
