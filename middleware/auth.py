from functools import wraps
from flask import request, jsonify, current_app # 新增 current_app
import jwt
# 移除 os，因為不再直接從環境變數讀取 SECRET_KEY
# import os
# 使用絕對路徑導入
from models.user import get_user_by_id, check_priority_level

# JWT 配置 - 移除這一行，將從 current_app.config 獲取
# JWT_SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-should-be-in-env')

def get_secret_key():
    """輔助函數：獲取並驗證 SECRET_KEY"""
    secret_key = current_app.config.get('SECRET_KEY')
    if not secret_key or secret_key == '!!DEFAULT_KEY_CHANGE_THIS_IN_PRODUCTION!!':
        current_app.logger.error(
            "CRITICAL: JWT SECRET_KEY is not set or is using the insecure default in config.py. "
            "Ensure SECRET_KEY environment variable is set for production."
        )
        # 在生產環境中，如果密鑰不安全，可能需要更嚴格的處理，例如拋出異常或阻止請求
        # 為了範例的簡單性，這裡我們仍然會嘗試使用它，但已記錄嚴重錯誤
        # 如果您的 .env 中有設定 SECRET_KEY (即使是 changeme...)，它會覆蓋 config.py 中的預設警告
        # 但最好的做法是如果 .env 中的值也不安全 (例如 'changeme...'), 也應視為問題
        if secret_key == 'changeme_in_production_to_a_strong_random_secret_key': # 檢查 .env 中的開發用密鑰
             current_app.logger.warning(
                 "WARNING: JWT SECRET_KEY is using a known development/default value from .env. "
                 "This is not secure for production."
             )
        # 如果要更安全，可以在這裡拋出異常阻止使用不安全的密鑰
        # raise ValueError("Insecure SECRET_KEY configuration.")
    return secret_key

def decode_token(token):
    """解碼 JWT 令牌"""
    secret_key = get_secret_key()
    if not secret_key: # 如果 get_secret_key 決定在密鑰不安全時返回 None 或拋出異常
        return None # 或者這裡應該根據 get_secret_key 的行為調整

    try:
        # 使用從 app.config 獲取的 SECRET_KEY
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        current_app.logger.warning("JWT token has expired.")
        return None  # 令牌已過期
    except jwt.InvalidTokenError as e:
        current_app.logger.warning(f"Invalid JWT token: {e}")
        return None  # 無效令牌
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred during token decoding: {e}")
        return None


def get_user_id_from_token(token):
    """從令牌獲取用戶 ID"""
    payload = decode_token(token)
    if payload:
        return payload.get('user_id')
    return None

def require_auth(f):
    """認證中間件裝飾器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"success": False, "message": "未授權：缺少 Authorization header"}), 401
        
        token_parts = auth_header.split(' ')
        if len(token_parts) != 2 or token_parts[0].lower() != 'bearer':
            return jsonify({"success": False, "message": "未授權：Authorization header 格式不正確"}), 401
        
        token = token_parts[1]
        payload = decode_token(token)
        
        if not payload:
            return jsonify({"success": False, "message": "無效的令牌或令牌已過期"}), 401
        
        user_id = payload.get('user_id')
        if not user_id:
            # 理論上 decode_token 成功，user_id 應該存在於 payload 中 (如果 generate_token 正確設置了)
            return jsonify({"success": False, "message": "無效的令牌：缺少 user_id"}), 401
        
        kwargs['user_id'] = user_id
        return f(*args, **kwargs)
    
    return decorated

def require_priority_level(level):
    """優先級別要求中間件裝飾器"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # require_auth 應該已經處理了 token 的基本驗證和 user_id 的提取
            # 但為了獨立性，或者如果此裝飾器可能在沒有 require_auth 的情況下使用，
            # 這裡可以重複 token 驗證邏輯，或者依賴於 user_id 已被注入 kwargs
            
            # 假設 require_auth 已經運行並將 user_id 放入 kwargs，或者此裝飾器總是與 require_auth 一起使用
            # 如果不是，則需要複製 require_auth 中的 token 提取和解碼邏輯

            # 以下為精簡版本，假設 user_id 已透過 require_auth 注入
            # 如果要使其完全獨立，請取消註解並調整下面的 token 處理部分
            
            # --- 如果需要獨立驗證，請複製 require_auth 的 token 處理邏輯於此 ---
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({"success": False, "message": "未授權"}), 401
            
            token = auth_header.split(' ')[1]
            payload = decode_token(token) # 使用更新後的 decode_token
            
            if not payload:
                return jsonify({"success": False, "message": "無效的令牌或令牌已過期"}), 401
            
            user_id_from_payload = payload.get('user_id') # 注意變數名稱，避免與 kwargs 中的 user_id 混淆
            if not user_id_from_payload:
                return jsonify({"success": False, "message": "無效的令牌"}), 401
            # --- 獨立驗證結束 ---

            # 檢查用戶優先級別
            # 使用從 token 中解析出的 user_id_from_payload 進行權限檢查
            if not check_priority_level(user_id_from_payload, level):
                return jsonify({"success": False, "message": f"權限不足：需要優先級別 {level} 或更高"}), 403
            
            # 將 user_id (來自 token) 傳遞給視圖函數，即使它可能已被 require_auth 設置
            kwargs['user_id'] = user_id_from_payload
            return f(*args, **kwargs)
        
        return decorated
    
    return decorator