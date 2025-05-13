from flask import Blueprint, request, jsonify
import jwt
import datetime
import os

# 確保使用絕對路徑導入
from models.user import (
    add_user, verify_password, get_user_by_id, 
    get_all_users, update_user, delete_user,
    set_user_work_status, check_priority_level
)
from middleware.auth import require_auth, require_priority_level

# 創建藍圖
auth_bp = Blueprint('auth', __name__, url_prefix='/api')

# 公開註冊路由
@auth_bp.route('/register', methods=['POST'])
def register():
    """公開註冊新用戶
    
    請求 JSON 格式:
    {
        "UserName": "用戶名稱",
        "UserID": "用戶ID",
        "Password": "密碼",
        ...其他用戶信息
    }
    """
    data = request.get_json()
    
    # 驗證必要字段
    required_fields = ['UserName', 'UserID', 'Password']
    for field in required_fields:
        if field not in data:
            return jsonify({
                "success": False,
                "message": f"缺少必要字段: {field}"
            }), 400
    
    # 設置默認優先級別為1（普通用戶）
    if 'PriorityLevel' not in data:
        data['PriorityLevel'] = 1
    
    try:
        new_user = add_user(data)
        
        if not new_user:
            return jsonify({
                "success": False,
                "message": "該用戶ID已被使用"
            }), 400
        
        # 移除敏感信息
        if 'Password' in new_user:
            del new_user['Password']
        
        return jsonify({
            "success": True,
            "message": "用戶創建成功",
            "user": new_user
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"創建用戶失敗: {str(e)}"
        }), 500

# JWT 配置
JWT_SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-should-be-in-env')
JWT_EXPIRATION_HOURS = 24  # 令牌有效期

def generate_token(user_id, user_name, priority_level):
    """產生 JWT 令牌"""
    payload = {
        'user_id': user_id,
        'user_name': user_name,
        'priority_level': priority_level,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')

@auth_bp.route('/login', methods=['POST'])
def login():
    """用戶登入
    
    請求 JSON 格式:
    {
        "user_id": "user123",
        "password": "secretpassword"
    }
    """
    data = request.get_json()
    user_id = data.get('user_id')
    password = data.get('password')

    if not user_id or not password:
        return jsonify({
            "success": False, 
            "message": "請提供用戶ID和密碼"
        }), 400

    # 驗證用戶
    try:
        user = verify_password(user_id, password)
        
        if not user:
            return jsonify({
                "success": False,
                "message": "用戶ID或密碼不正確"
            }), 401
        
        # 使用 JWT
        token = generate_token(
            user['ID'], 
            user['UserName'], 
            user['PriorityLevel']
        )
        
        # 更新用戶工作狀態
        set_user_work_status(user['ID'], True)
        
        return jsonify({
            "success": True,
            "message": "登入成功",
            "token": token,
            "user": {
                "id": user['ID'],
                "userName": user['UserName'],
                "userID": user['UserID'],
                "priorityLevel": user['PriorityLevel'],
                "position": user['Position'],
                "department": user['Department']
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"登入失敗: {str(e)}"
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout(user_id):
    """用戶登出"""
    try:
        # 更新用戶工作狀態
        set_user_work_status(user_id, False)
        
        return jsonify({
            "success": True,
            "message": "登出成功"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"登出失敗: {str(e)}"
        }), 500

@auth_bp.route('/users', methods=['GET'])
@require_priority_level(2)  # 需要較高優先級別
def get_users(user_id):
    """獲取所有用戶"""
    try:
        users = get_all_users()
        
        # 移除敏感信息
        for user in users:
            if 'Password' in user:
                del user['Password']
        
        return jsonify({
            "success": True,
            "users": users
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"獲取用戶列表失敗: {str(e)}"
        }), 500

@auth_bp.route('/users', methods=['POST'])
@require_priority_level(3)  # 需要高優先級別
def create_user(user_id):
    """創建新用戶"""
    data = request.get_json()
    
    # 驗證必要字段
    required_fields = ['UserName', 'UserID', 'Password', 'PriorityLevel']
    for field in required_fields:
        if field not in data:
            return jsonify({
                "success": False,
                "message": f"缺少必要字段: {field}"
            }), 400
    
    try:
        new_user = add_user(data)
        
        if not new_user:
            return jsonify({
                "success": False,
                "message": "該用戶ID已被使用"
            }), 400
        
        # 移除敏感信息
        if 'Password' in new_user:
            del new_user['Password']
        
        return jsonify({
            "success": True,
            "message": "用戶創建成功",
            "user": new_user
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"創建用戶失敗: {str(e)}"
        }), 500

@auth_bp.route('/users/<int:target_user_id>', methods=['PUT'])
@require_priority_level(3)  # 需要高優先級別
def update_user_info(user_id, target_user_id):
    """更新用戶信息"""
    data = request.get_json()
    
    # 檢查是否嘗試提升權限
    if 'PriorityLevel' in data:
        # 獲取當前用戶的優先級別
        current_user = get_user_by_id(user_id)
        if not current_user or data['PriorityLevel'] > current_user['PriorityLevel']:
            return jsonify({
                "success": False,
                "message": "無法設置高於自己的優先級別"
            }), 403
    
    try:
        updated_user = update_user(target_user_id, data)
        
        if not updated_user:
            return jsonify({
                "success": False,
                "message": "用戶不存在"
            }), 404
        
        # 移除敏感信息
        if 'Password' in updated_user:
            del updated_user['Password']
        
        return jsonify({
            "success": True,
            "message": "用戶更新成功",
            "user": updated_user
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"更新用戶失敗: {str(e)}"
        }), 500

@auth_bp.route('/users/<int:target_user_id>', methods=['DELETE'])
@require_priority_level(3)  # 需要高優先級別
def delete_user_account(user_id, target_user_id):
    """刪除用戶"""
    # 檢查是否嘗試刪除自己
    if user_id == target_user_id:
        return jsonify({
            "success": False,
            "message": "無法刪除自己的帳戶"
        }), 400
    
    # 檢查是否嘗試刪除更高優先級別的用戶
    current_user = get_user_by_id(user_id)
    target_user = get_user_by_id(target_user_id)
    
    if not current_user or not target_user:
        return jsonify({
            "success": False,
            "message": "用戶不存在"
        }), 404
    
    if target_user['PriorityLevel'] > current_user['PriorityLevel']:
        return jsonify({
            "success": False,
            "message": "無法刪除優先級別高於自己的用戶"
        }), 403
    
    try:
        success = delete_user(target_user_id)
        
        if not success:
            return jsonify({
                "success": False,
                "message": "刪除用戶失敗"
            }), 500
        
        return jsonify({
            "success": True,
            "message": "用戶刪除成功"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"刪除用戶失敗: {str(e)}"
        }), 500

@auth_bp.route('/profile', methods=['GET'])
@require_auth
def get_profile(user_id):
    """獲取用戶個人資料"""
    try:
        user = get_user_by_id(user_id)
        
        if not user:
            return jsonify({
                "success": False,
                "message": "用戶不存在"
            }), 404
        
        # 移除敏感信息
        if 'Password' in user:
            del user['Password']
        
        return jsonify({
            "success": True,
            "user": user
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"獲取用戶資料失敗: {str(e)}"
        }), 500

@auth_bp.route('/change_password', methods=['POST'])
@require_auth
def change_password(user_id):
    """修改密碼"""
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({
            "success": False,
            "message": "請提供舊密碼和新密碼"
        }), 400
    
    try:
        # 獲取用戶信息
        user = get_user_by_id(user_id)
        
        if not user:
            return jsonify({
                "success": False,
                "message": "用戶不存在"
            }), 404
        
        # 驗證舊密碼
        verified_user = verify_password(user['UserID'], old_password)
        
        if not verified_user:
            return jsonify({
                "success": False,
                "message": "舊密碼不正確"
            }), 401
        
        # 更新密碼
        updated_user = update_user(user_id, {'Password': new_password})
        
        if not updated_user:
            return jsonify({
                "success": False,
                "message": "更新密碼失敗"
            }), 500
        
        return jsonify({
            "success": True,
            "message": "密碼更新成功"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"更新密碼失敗: {str(e)}"
        }), 500
