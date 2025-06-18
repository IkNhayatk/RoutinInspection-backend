from flask import Blueprint, request, jsonify, current_app # 新增 current_app
import jwt
import datetime
# 移除 os，因為不再直接從環境變數讀取 SECRET_KEY
# import os

# 確保使用絕對路徑導入
from models.user import (
    add_user, verify_password, get_user_by_id, 
    get_all_users, get_all_users_with_signing_data, get_user_with_signing_data,
    update_user, delete_user, set_user_work_status, check_priority_level,
    validate_user_data_consistency, fix_user_data_consistency
)
from middleware.auth import require_auth, require_priority_level # middleware.auth 自身已更新

# 創建藍圖
auth_bp = Blueprint('auth', __name__, url_prefix='/api')

# 公開註冊路由 (保持不變，除非有特定與 SECRET_KEY 相關的邏輯)
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    required_fields = ['UserName', 'UserID', 'Password']
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "message": f"缺少必要字段: {field}"}), 400
    if 'PriorityLevel' not in data:
        data['PriorityLevel'] = 1
    try:
        new_user = add_user(data)
        if not new_user:
            return jsonify({"success": False, "message": "該用戶ID已被使用"}), 400
        if 'Password' in new_user:
            del new_user['Password']
        return jsonify({"success": True, "message": "用戶創建成功", "user": new_user})
    except Exception as e:
        current_app.logger.error(f"創建用戶失敗: {str(e)}")
        return jsonify({"success": False, "message": f"創建用戶失敗: {str(e)}"}), 500

# JWT 配置 - 移除這一行，將從 current_app.config 獲取
# JWT_SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-should-be-in-env')
JWT_EXPIRATION_HOURS = 24  # 令牌有效期 (這個可以保留，或者也移到 config)

def generate_token(user_id, user_name, priority_level):
    """產生 JWT 令牌"""
    secret_key = current_app.config.get('SECRET_KEY') # 從 app.config 獲取
    
    # 與 middleware/auth.py 中類似的檢查邏輯
    if not secret_key or secret_key == '!!DEFAULT_KEY_CHANGE_THIS_IN_PRODUCTION!!':
        current_app.logger.error(
            "CRITICAL: JWT SECRET_KEY is not set or is using the insecure default in config.py for token generation."
        )
        # 如果 .env 中有設定 SECRET_KEY (即使是 changeme...)，它會覆蓋 config.py 中的預設警告
        if secret_key == 'changeme_in_production_to_a_strong_random_secret_key': # 檢查 .env 中的開發用密鑰
             current_app.logger.warning(
                 "WARNING: JWT SECRET_KEY is using a known development/default value from .env for token generation. "
                 "This is not secure for production."
             )
        # 強制要求安全的密鑰才能產生 token
        raise ValueError("Cannot generate token: SECRET_KEY is not securely configured.")

    payload = {
        'user_id': user_id,
        'user_name': user_name,
        'priority_level': priority_level,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user_id_input = data.get('user_id') # 避免與 models.user.get_user_by_id 的參數名衝突
    password = data.get('password')

    if not user_id_input or not password:
        return jsonify({"success": False, "message": "請提供用戶ID和密碼"}), 400

    try:
        user = verify_password(user_id_input, password) # 使用 verify_password
        if not user:
            return jsonify({"success": False, "message": "用戶ID或密碼不正確"}), 401
        
        token = generate_token( # 使用更新後的 generate_token
            user['ID'], 
            user['UserName'], 
            user['PriorityLevel']
        )
        
        set_user_work_status(user['ID'], True)
        
        return jsonify({
            "success": True,
            "message": "登入成功",
            "token": token,
            "user": {
                "id": user['ID'],
                "userName": user['UserName'],
                "userID": user['UserID'], # 注意 SysUser 表中的 UserID 欄位
                "priorityLevel": user['PriorityLevel'],
                "position": user.get('Position'), # 使用 .get() 避免 Key Error
                "department": user.get('Department')
            }
        })
    except ValueError as ve: # 捕獲 generate_token 中可能因密鑰問題拋出的 ValueError
        current_app.logger.error(f"登入失敗 (Value Error in token generation): {str(ve)}")
        return jsonify({"success": False, "message": f"登入失敗：內部配置錯誤"}), 500
    except Exception as e:
        current_app.logger.error(f"登入失敗: {str(e)}")
        return jsonify({"success": False, "message": f"登入失敗: {str(e)}"}), 500

# 其他路由 (logout, get_users, create_user, update_user_info, delete_user_account, get_profile, change_password)
# 通常不需要直接處理 SECRET_KEY，因為它們依賴於 @require_auth 或 @require_priority_level，
# 而這些裝飾器現在會使用更新後的 token 解碼邏輯。
# 所以，這些路由的程式碼可以保持大致不變，除非您想在錯誤處理中加入更詳細的日誌。

# ... (此處省略其他路由的程式碼，假設它們的邏輯不直接依賴於 SECRET_KEY 的獲取)
# 例如 /logout:
@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout(user_id): # user_id 由 @require_auth 注入
    """用戶登出"""
    try:
        set_user_work_status(user_id, False)
        return jsonify({"success": True, "message": "登出成功"})
    except Exception as e:
        current_app.logger.error(f"登出失敗: {str(e)}")
        return jsonify({"success": False, "message": f"登出失敗: {str(e)}"}), 500

# ... (其他路由類似)
@auth_bp.route('/users', methods=['GET'])
@require_priority_level(1)
def get_users(user_id): # user_id 由 @require_priority_level 注入
    try:
        current_app.logger.info(f"GET /users - user_id: {user_id}")
        users = get_all_users_with_signing_data()
        for user in users:
            if 'Password' in user: del user['Password']
        current_app.logger.info(f"Successfully retrieved {len(users)} users")
        return jsonify({"success": True, "users": users})
    except Exception as e:
        current_app.logger.error(f"獲取用戶列表失敗: {str(e)}")
        return jsonify({"success": False, "message": f"獲取用戶列表失敗: {str(e)}"}), 500

@auth_bp.route('/users', methods=['POST'])
@require_priority_level(3)
def create_user(user_id): # user_id 由 @require_priority_level 注入 (雖然此操作可能不需要操作者 user_id)
    data = request.get_json()
    required_fields = ['userName', 'userID', 'email', 'priorityLevel']
    
    # 檢查必要字段（使用前端的字段名）
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "message": f"缺少必要字段: {field}"}), 400
    
    # 轉換前端字段名到後端字段名
    backend_data = {
        'UserName': data.get('userName'),
        'UserID': data.get('userID'),
        'EngName': data.get('engName', ''),
        'Email': data.get('email'),
        'Password': data.get('password', ''),
        'PriorityLevel': data.get('priorityLevel'),
        'Position': data.get('position', ''),
        'Department': data.get('department', ''),
        'Remark': data.get('remark', ''),
        'isAtWork': data.get('isAtWork', True),
        'signingData': data.get('signingData')
    }
    
    # 如果沒有提供密碼，使用預設密碼（UserID的後6位）
    if not backend_data['Password']:
        user_id_str = backend_data['UserID']
        backend_data['Password'] = user_id_str[-6:] if len(user_id_str) >= 6 else user_id_str
    
    try:
        new_user = add_user(backend_data)
        if not new_user: 
            return jsonify({"success": False, "message": "該用戶ID已被使用"}), 400
        if 'Password' in new_user: 
            del new_user['Password']
        return jsonify({"success": True, "message": "用戶創建成功", "user": new_user})
    except Exception as e:
        current_app.logger.error(f"創建用戶失敗 (admin): {str(e)}")
        return jsonify({"success": False, "message": f"創建用戶失敗: {str(e)}"}), 500

@auth_bp.route('/users/<int:target_user_id>', methods=['PUT'])
@require_priority_level(3)
def update_user_info(user_id, target_user_id): # user_id 是操作者ID, target_user_id 是被操作者ID
    data = request.get_json()
    
    # 轉換前端字段名到後端字段名
    backend_data = {}
    
    # 處理基本用戶信息
    field_mapping = {
        'userName': 'UserName',
        'userID': 'UserID',
        'engName': 'EngName',
        'email': 'Email',
        'password': 'Password',
        'priorityLevel': 'PriorityLevel',
        'position': 'Position',
        'department': 'Department',
        'remark': 'Remark',
        'isAtWork': 'isAtWork'
    }
    
    for frontend_key, backend_key in field_mapping.items():
        if frontend_key in data:
            backend_data[backend_key] = data[frontend_key]
    
    # 處理核簽資料
    if 'signingData' in data:
        backend_data['signingData'] = data['signingData']
    
    # 權限檢查
    if 'PriorityLevel' in backend_data:
        current_operator = get_user_by_id(user_id) # 操作者
        if not current_operator or backend_data['PriorityLevel'] > current_operator['PriorityLevel']:
            return jsonify({"success": False, "message": "無法設置高於自己的優先級別"}), 403
    
    try:
        updated_user = update_user(target_user_id, backend_data)
        if not updated_user: 
            return jsonify({"success": False, "message": "用戶不存在"}), 404
        if 'Password' in updated_user: 
            del updated_user['Password']
        return jsonify({"success": True, "message": "用戶更新成功", "user": updated_user})
    except Exception as e:
        current_app.logger.error(f"更新用戶失敗 (admin): {str(e)}")
        return jsonify({"success": False, "message": f"更新用戶失敗: {str(e)}"}), 500

@auth_bp.route('/users/<int:target_user_id>', methods=['DELETE'])
@require_priority_level(3)
def delete_user_account(user_id, target_user_id): # user_id 是操作者ID
    if user_id == target_user_id:
        return jsonify({"success": False, "message": "無法刪除自己的帳戶"}), 400
    current_operator = get_user_by_id(user_id)
    target_user_to_delete = get_user_by_id(target_user_id)
    if not current_operator or not target_user_to_delete:
        return jsonify({"success": False, "message": "用戶不存在"}), 404
    if target_user_to_delete['PriorityLevel'] > current_operator['PriorityLevel']:
        return jsonify({"success": False, "message": "無法刪除優先級別高於自己的用戶"}), 403
    try:
        success = delete_user(target_user_id)
        if not success: return jsonify({"success": False, "message": "刪除用戶失敗"}), 500
        return jsonify({"success": True, "message": "用戶刪除成功"})
    except Exception as e:
        current_app.logger.error(f"刪除用戶失敗 (admin): {str(e)}")
        return jsonify({"success": False, "message": f"刪除用戶失敗: {str(e)}"}), 500

@auth_bp.route('/profile', methods=['GET'])
@require_auth
def get_profile(user_id): # user_id 由 @require_auth 注入
    try:
        user = get_user_with_signing_data(user_id)
        if not user: return jsonify({"success": False, "message": "用戶不存在"}), 404
        if 'Password' in user: del user['Password']
        return jsonify({"success": True, "user": user})
    except Exception as e:
        current_app.logger.error(f"獲取用戶資料失敗: {str(e)}")
        return jsonify({"success": False, "message": f"獲取用戶資料失敗: {str(e)}"}), 500

@auth_bp.route('/change_password', methods=['POST'])
@require_auth
def change_password(user_id): # user_id 由 @require_auth 注入
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    if not old_password or not new_password:
        return jsonify({"success": False, "message": "請提供舊密碼和新密碼"}), 400
    try:
        user = get_user_by_id(user_id)
        if not user: return jsonify({"success": False, "message": "用戶不存在"}), 404
        
        # 注意：verify_password 通常接收 UserID (字串型態的登入ID), 而不是資料庫的 int ID
        # 確保 get_user_by_id 返回的 user 物件中有 UserID 欄位
        if 'UserID' not in user:
            current_app.logger.error(f"UserID field missing in user object for ID: {user_id}")
            return jsonify({"success": False, "message": "驗證用戶資訊時發生錯誤"}), 500

        verified_user = verify_password(user['UserID'], old_password)
        if not verified_user:
            return jsonify({"success": False, "message": "舊密碼不正確"}), 401
        
        updated_user_result = update_user(user_id, {'Password': new_password}) # update_user 接收 int user_id
        if not updated_user_result:
            return jsonify({"success": False, "message": "更新密碼失敗"}), 500
        
        return jsonify({"success": True, "message": "密碼更新成功"})
    except Exception as e:
        current_app.logger.error(f"更新密碼失敗: {str(e)}")
        return jsonify({"success": False, "message": f"更新密碼失敗: {str(e)}"}), 500

# Admin endpoints for data consistency management
@auth_bp.route('/admin/users/validate-consistency', methods=['GET'])
@require_priority_level(3)
def validate_all_users_consistency(user_id):
    """驗證所有用戶的資料一致性"""
    try:
        users = get_all_users()
        results = []
        
        for user in users:
            validation_result = validate_user_data_consistency(user['ID'])
            results.append({
                'user_id': user['ID'],
                'user_name': user.get('UserName'),
                'user_id_str': user.get('UserID'),
                'is_consistent': validation_result['is_consistent'],
                'issues': validation_result['issues']
            })
        
        inconsistent_count = sum(1 for r in results if not r['is_consistent'])
        
        return jsonify({
            "success": True,
            "message": f"驗證完成，共{len(results)}個用戶，{inconsistent_count}個有一致性問題",
            "total_users": len(results),
            "inconsistent_users": inconsistent_count,
            "results": results
        })
    except Exception as e:
        current_app.logger.error(f"驗證用戶一致性失敗: {str(e)}")
        return jsonify({"success": False, "message": f"驗證失敗: {str(e)}"}), 500

@auth_bp.route('/admin/users/<int:target_user_id>/validate-consistency', methods=['GET'])
@require_priority_level(3)
def validate_user_consistency(user_id, target_user_id):
    """驗證特定用戶的資料一致性"""
    try:
        validation_result = validate_user_data_consistency(target_user_id)
        user = get_user_by_id(target_user_id)
        
        if not user:
            return jsonify({"success": False, "message": "用戶不存在"}), 404
        
        return jsonify({
            "success": True,
            "user_id": target_user_id,
            "user_name": user.get('UserName'),
            "user_id_str": user.get('UserID'),
            "is_consistent": validation_result['is_consistent'],
            "issues": validation_result['issues']
        })
    except Exception as e:
        current_app.logger.error(f"驗證用戶一致性失敗: {str(e)}")
        return jsonify({"success": False, "message": f"驗證失敗: {str(e)}"}), 500

@auth_bp.route('/admin/users/<int:target_user_id>/fix-consistency', methods=['POST'])
@require_priority_level(3)
def fix_user_consistency(user_id, target_user_id):
    """修復特定用戶的資料一致性問題"""
    try:
        success = fix_user_data_consistency(target_user_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"用戶 {target_user_id} 的資料一致性已修復"
            })
        else:
            return jsonify({
                "success": False,
                "message": f"修復用戶 {target_user_id} 的資料一致性失敗"
            }), 500
    except Exception as e:
        current_app.logger.error(f"修復用戶一致性失敗: {str(e)}")
        return jsonify({"success": False, "message": f"修復失敗: {str(e)}"}), 500

@auth_bp.route('/admin/users/fix-all-consistency', methods=['POST'])
@require_priority_level(3)
def fix_all_users_consistency(user_id):
    """修復所有用戶的資料一致性問題"""
    try:
        users = get_all_users()
        results = []
        success_count = 0
        
        for user in users:
            try:
                success = fix_user_data_consistency(user['ID'])
                results.append({
                    'user_id': user['ID'],
                    'user_name': user.get('UserName'),
                    'success': success
                })
                if success:
                    success_count += 1
            except Exception as e:
                results.append({
                    'user_id': user['ID'],
                    'user_name': user.get('UserName'),
                    'success': False,
                    'error': str(e)
                })
        
        return jsonify({
            "success": True,
            "message": f"批量修復完成，共處理{len(results)}個用戶，成功{success_count}個",
            "total_users": len(results),
            "success_count": success_count,
            "results": results
        })
    except Exception as e:
        current_app.logger.error(f"批量修復用戶一致性失敗: {str(e)}")
        return jsonify({"success": False, "message": f"批量修復失敗: {str(e)}"}), 500