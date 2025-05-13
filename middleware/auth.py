from functools import wraps
from flask import request, jsonify, current_app
import jwt
import os
# 使用絕對路徑導入
from models.user import get_user_by_id, check_priority_level

# JWT 配置
JWT_SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-should-be-in-env')

def decode_token(token):
    """解碼 JWT 令牌
    
    Args:
        token (str): JWT 令牌
        
    Returns:
        dict: 令牌負載或 None（如果令牌無效）
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # 令牌已過期
    except jwt.InvalidTokenError:
        return None  # 無效令牌

def get_user_id_from_token(token):
    """從令牌獲取用戶 ID
    
    使用 JWT 令牌系統獲取用戶 ID。
    
    Args:
        token (str): JWT 令牌
        
    Returns:
        int: 用戶 ID 或 None
    """
    payload = decode_token(token)
    if payload:
        return payload.get('user_id')
    return None

def require_auth(f):
    """認證中間件裝飾器
    
    確保請求必須包含有效的 JWT 認證令牌才能訪問受保護的路由
    
    Args:
        f: 被裝飾的視圖函數
        
    Returns:
        function: 包裝後的視圖函數
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"success": False, "message": "未授權"}), 401
        
        token = auth_header.split(' ')[1]
        payload = decode_token(token)
        
        if not payload:
            return jsonify({"success": False, "message": "無效的令牌或令牌已過期"}), 401
        
        user_id = payload.get('user_id')
        if not user_id:
            return jsonify({"success": False, "message": "無效的令牌"}), 401
        
        kwargs['user_id'] = user_id
        return f(*args, **kwargs)
    
    return decorated

def require_priority_level(level):
    """優先級別要求中間件裝飾器
    
    確保只有具有指定優先級別的用戶可以訪問受保護的路由
    
    Args:
        level (int): 所需的優先級別
        
    Returns:
        function: 裝飾器函數
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({"success": False, "message": "未授權"}), 401
            
            token = auth_header.split(' ')[1]
            payload = decode_token(token)
            
            if not payload:
                return jsonify({"success": False, "message": "無效的令牌或令牌已過期"}), 401
            
            user_id = payload.get('user_id')
            if not user_id:
                return jsonify({"success": False, "message": "無效的令牌"}), 401
            
            # 檢查用戶優先級別
            if not check_priority_level(user_id, level):
                return jsonify({"success": False, "message": f"需要優先級別 {level} 或更高"}), 403
            
            kwargs['user_id'] = user_id
            return f(*args, **kwargs)
        
        return decorated
    
    return decorator
