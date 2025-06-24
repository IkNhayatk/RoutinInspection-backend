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
        
        # 獲取查詢參數
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))
        search_keyword = request.args.get('search', '').strip()
        
        # 參數驗證
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10
        
        # 獲取當前用戶信息，用於權限控制
        current_user = get_user_by_id(user_id)
        if not current_user:
            return jsonify({"success": False, "message": "無法獲取當前用戶信息"}), 404
            
        # 獲取所有用戶數據
        all_users = get_all_users_with_signing_data()
        
        # 移除密碼字段
        for user in all_users:
            if 'Password' in user: 
                del user['Password']
        
        # 根據權限級別過濾用戶
        current_priority = current_user.get('PriorityLevel', 1)
        current_department = current_user.get('Department', '')
        
        if current_priority >= 3:
            # 優先級別3和4可以看到所有用戶
            accessible_users = all_users
            current_app.logger.info(f"User {user_id} (priority {current_priority}) can see all users")
        else:
            # 優先級別1和2只能看到部門前3碼相同的用戶
            current_dept_prefix = current_department[:3] if current_department else ''
            accessible_users = []
            
            for user in all_users:
                user_department = user.get('Department', '')
                user_dept_prefix = user_department[:3] if user_department else ''
                
                # 如果部門前3碼相同，或者是自己，則可見
                if user_dept_prefix == current_dept_prefix or user.get('ID') == user_id:
                    accessible_users.append(user)
            
            current_app.logger.info(f"User {user_id} (priority {current_priority}, dept prefix '{current_dept_prefix}') can see {len(accessible_users)} users")
        
        # 根據搜索關鍵字過濾（搜索用戶ID）
        if search_keyword:
            filtered_users = [
                user for user in accessible_users 
                if search_keyword.lower() in str(user.get('UserID', '')).lower()
            ]
        else:
            filtered_users = accessible_users
        
        # 計算分頁信息
        total_count = len(filtered_users)
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        
        # 計算分頁範圍
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_users = filtered_users[start_index:end_index]
        
        current_app.logger.info(f"Successfully retrieved {len(paginated_users)} users (page {page}/{total_pages}, total: {total_count})")
        
        return jsonify({
            "success": True,
            "users": paginated_users,
            "pagination": {
                "current_page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        })
    except ValueError as ve:
        current_app.logger.error(f"參數錯誤: {str(ve)}")
        return jsonify({"success": False, "message": "分頁參數格式錯誤"}), 400
    except Exception as e:
        current_app.logger.error(f"獲取用戶列表失敗: {str(e)}")
        return jsonify({"success": False, "message": f"獲取用戶列表失敗: {str(e)}"}), 500

@auth_bp.route('/users', methods=['POST'])
@require_priority_level(1)
def create_user(user_id): # user_id 由 @require_priority_level 注入 (雖然此操作可能不需要操作者 user_id)
    data = request.get_json()
    required_fields = ['userName', 'userID', 'email', 'priorityLevel']
    
    # 檢查必要字段（使用前端的字段名）
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "message": f"缺少必要字段: {field}"}), 400
    
    # 獲取當前用戶信息，用於權限控制
    current_user = get_user_by_id(user_id)
    if not current_user:
        return jsonify({"success": False, "message": "無法獲取當前用戶信息"}), 404
    
    current_priority = current_user.get('PriorityLevel', 1)
    current_department = current_user.get('Department', '')
    
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
    
    # 部門權限檢查：級別1和2只能創建同部門前3碼的用戶
    if current_priority < 3:
        current_dept_prefix = current_department[:3] if current_department else ''
        new_user_department = backend_data.get('Department', '')
        new_user_dept_prefix = new_user_department[:3] if new_user_department else ''
        
        if new_user_dept_prefix != current_dept_prefix:
            return jsonify({
                "success": False, 
                "message": f"您只能創建部門前3碼與您相同({current_dept_prefix})的用戶"
            }), 403
    
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
@require_priority_level(1)
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
    
    # 獲取當前用戶信息，用於權限控制
    current_operator = get_user_by_id(user_id) # 操作者
    if not current_operator:
        return jsonify({"success": False, "message": "無法獲取當前用戶信息"}), 404
    
    current_priority = current_operator.get('PriorityLevel', 1)
    current_department = current_operator.get('Department', '')
    
    # 部門權限檢查：級別1和2只能修改同部門前3碼的用戶
    if current_priority < 3:
        target_user = get_user_by_id(target_user_id)
        if not target_user:
            return jsonify({"success": False, "message": "目標用戶不存在"}), 404
        
        current_dept_prefix = current_department[:3] if current_department else ''
        target_dept_prefix = target_user.get('Department', '')[:3] if target_user.get('Department') else ''
        
        # 檢查是否有權限修改這個用戶（同部門前3碼或者是自己）
        if target_dept_prefix != current_dept_prefix and target_user_id != user_id:
            return jsonify({
                "success": False, 
                "message": f"您只能修改部門前3碼與您相同({current_dept_prefix})的用戶"
            }), 403
        
        # 如果修改部門，檢查新部門是否符合權限
        if 'Department' in backend_data:
            new_dept_prefix = backend_data['Department'][:3] if backend_data['Department'] else ''
            if new_dept_prefix != current_dept_prefix:
                return jsonify({
                    "success": False, 
                    "message": f"您只能將用戶的部門設置為與您相同前3碼({current_dept_prefix})的部門"
                }), 403
    
    # 權限檢查
    if 'PriorityLevel' in backend_data:
        if backend_data['PriorityLevel'] > current_operator['PriorityLevel']:
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
@require_priority_level(1)
def delete_user_account(user_id, target_user_id): # user_id 是操作者ID
    if user_id == target_user_id:
        return jsonify({"success": False, "message": "無法刪除自己的帳戶"}), 400
    
    current_operator = get_user_by_id(user_id)
    target_user_to_delete = get_user_by_id(target_user_id)
    if not current_operator or not target_user_to_delete:
        return jsonify({"success": False, "message": "用戶不存在"}), 404
    
    current_priority = current_operator.get('PriorityLevel', 1)
    current_department = current_operator.get('Department', '')
    
    # 部門權限檢查：級別1和2只能刪除同部門前3碼的用戶
    if current_priority < 3:
        current_dept_prefix = current_department[:3] if current_department else ''
        target_dept_prefix = target_user_to_delete.get('Department', '')[:3] if target_user_to_delete.get('Department') else ''
        
        if target_dept_prefix != current_dept_prefix:
            return jsonify({
                "success": False, 
                "message": f"您只能刪除部門前3碼與您相同({current_dept_prefix})的用戶"
            }), 403
    
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

@auth_bp.route('/users/bulk-import', methods=['POST'])
@require_priority_level(1)
def bulk_import_users(user_id):
    """批量匯入用戶 - 只允許優先級別1和2的用戶使用，並限制在同部門前3碼"""
    import csv
    import io
    
    try:
        # 檢查是否有上傳的檔案
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "未找到上傳檔案"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "message": "未選擇檔案"}), 400
            
        # 檢查檔案類型
        allowed_extensions = ['.csv', '.xlsx', '.xls']
        if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
            return jsonify({"success": False, "message": "只支援CSV或Excel檔案"}), 400
        
        # 獲取當前用戶資訊，用於權限控制
        current_user = get_user_by_id(user_id)
        if not current_user:
            return jsonify({"success": False, "message": "無法獲取當前用戶信息"}), 404
            
        current_priority = current_user.get('PriorityLevel', 1)
        current_department = current_user.get('Department', '')
        current_dept_prefix = current_department[:3] if current_department else ''
        
        # 只允許優先級別1和2使用批量匯入功能
        if current_priority > 2:
            return jsonify({
                "success": False, 
                "message": "批量匯入功能只開放給優先級別1和2的用戶使用"
            }), 403
        
        # 讀取檔案內容
        file_content = file.read().decode('utf-8-sig')  # 處理BOM
        csv_reader = csv.reader(io.StringIO(file_content))
        
        # 跳過標題行
        headers = next(csv_reader, None)
        if not headers:
            return jsonify({"success": False, "message": "檔案格式錯誤：找不到標題行"}), 400
        
        # 預期的CSV欄位（按順序）
        expected_headers = [
            '巡檢人姓名', '巡檢人ID', '主管姓名', '主管ID', '課長姓名', '課長ID',
            '廠工安人員1', '廠工安人員1ID', '廠PSM專人姓名', '廠PSM專人ID',
            '廠長姓名', '廠長ID', '工安主管姓名', '工安主管ID', '工安高專姓名', '工安高專ID',
            '廠', '課', '部門', '部門縮寫', '職稱', '第二部門', 'PriorityLevel'
        ]
        
        # 驗證標題
        if len(headers) < len(expected_headers):
            return jsonify({
                "success": False, 
                "message": f"檔案格式錯誤：欄位數量不足，預期{len(expected_headers)}個欄位，實際{len(headers)}個"
            }), 400
        
        imported_users = []
        import_errors = []
        row_number = 1  # 從資料行開始計數
        
        for row in csv_reader:
            row_number += 1
            if len(row) < len(expected_headers):
                import_errors.append(f"第{row_number}行：欄位數量不足")
                continue
            
            try:
                # 提取基本用戶資訊
                user_name = row[0].strip()
                user_id_str = row[1].strip()
                department = row[18].strip()  # 部門
                priority_level = int(row[22].strip()) if row[22].strip() else 1
                
                # 檢查必要欄位
                if not user_name or not user_id_str:
                    import_errors.append(f"第{row_number}行：巡檢人姓名和ID不能為空")
                    continue
                
                # 檢查優先級別限制：只能匯入級別1和2的用戶
                if priority_level not in [1, 2]:
                    import_errors.append(f"第{row_number}行：只能匯入優先級別1和2的用戶，實際為級別{priority_level}")
                    continue
                
                # 部門權限檢查：只能匯入同部門前3碼的用戶
                user_dept_prefix = department[:3] if department else ''
                if user_dept_prefix != current_dept_prefix:
                    import_errors.append(f"第{row_number}行：只能匯入部門前3碼與您相同({current_dept_prefix})的用戶，實際為{user_dept_prefix}")
                    continue
                
                # 準備用戶資料
                user_data = {
                    'UserName': user_name,
                    'UserID': user_id_str,
                    'EngName': '',  # CSV中沒有英文名，設為空
                    'Email': '',    # CSV中沒有email，設為空
                    'Password': '',  # 將使用預設密碼（UserID後6位）
                    'PriorityLevel': priority_level,
                    'Position': row[20].strip() if len(row) > 20 else '',  # 職稱
                    'Department': department,
                    'Remark': '',
                    'isAtWork': True,
                    'signingData': {
                        # 主管資訊
                        'supervisorName': row[2].strip() if len(row) > 2 else '',
                        'supervisorID': row[3].strip() if len(row) > 3 else '',
                        # 課長資訊
                        'sectionChiefName': row[4].strip() if len(row) > 4 else '',
                        'sectionChiefID': row[5].strip() if len(row) > 5 else '',
                        # 工安人員資訊
                        'safetyOfficer1': row[6].strip() if len(row) > 6 else '',
                        'safetyOfficer1ID': row[7].strip() if len(row) > 7 else '',
                        # PSM專人資訊
                        'psmSpecialistName': row[8].strip() if len(row) > 8 else '',
                        'psmSpecialistID': row[9].strip() if len(row) > 9 else '',
                        # 廠長資訊
                        'factoryManagerName': row[10].strip() if len(row) > 10 else '',
                        'factoryManagerID': row[11].strip() if len(row) > 11 else '',
                        # 工安主管資訊
                        'safetySupervisorName': row[12].strip() if len(row) > 12 else '',
                        'safetySupervisorID': row[13].strip() if len(row) > 13 else '',
                        # 工安高專資訊
                        'safetySpecialistName': row[14].strip() if len(row) > 14 else '',
                        'safetySpecialistID': row[15].strip() if len(row) > 15 else '',
                        # 部門相關資訊
                        'factory': row[16].strip() if len(row) > 16 else '',
                        'section': row[17].strip() if len(row) > 17 else '',
                        'departmentAbbr': row[19].strip() if len(row) > 19 else '',
                        'secondDepartment': row[21].strip() if len(row) > 21 else ''
                    }
                }
                
                # 如果沒有提供密碼，使用預設密碼（UserID的後6位）
                if not user_data['Password']:
                    user_data['Password'] = user_id_str[-6:] if len(user_id_str) >= 6 else user_id_str
                
                # 嘗試創建用戶
                new_user = add_user(user_data)
                if new_user:
                    imported_users.append({
                        'row': row_number,
                        'user_name': user_name,
                        'user_id': user_id_str,
                        'priority_level': priority_level
                    })
                else:
                    import_errors.append(f"第{row_number}行：用戶ID {user_id_str} 已存在")
                    
            except ValueError as ve:
                import_errors.append(f"第{row_number}行：資料格式錯誤 - {str(ve)}")
            except Exception as e:
                import_errors.append(f"第{row_number}行：處理失敗 - {str(e)}")
        
        # 回傳結果
        success_count = len(imported_users)
        error_count = len(import_errors)
        
        current_app.logger.info(f"批量匯入完成 - 成功：{success_count}，失敗：{error_count}")
        
        response_data = {
            "success": True,
            "imported_count": success_count,
            "error_count": error_count,
            "message": f"匯入完成：成功 {success_count} 個，失敗 {error_count} 個",
            "imported_users": imported_users
        }
        
        if import_errors:
            response_data["errors"] = import_errors
        
        return jsonify(response_data)
        
    except UnicodeDecodeError:
        return jsonify({"success": False, "message": "檔案編碼錯誤，請確保使用UTF-8編碼"}), 400
    except Exception as e:
        current_app.logger.error(f"批量匯入失敗: {str(e)}")
        return jsonify({"success": False, "message": f"批量匯入失敗: {str(e)}"}), 500