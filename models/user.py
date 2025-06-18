import bcrypt
from flask import current_app
# 使用絕對路徑導入
from db import execute_query, get_db

def add_signing_data(user_id, user_name, user_id_str, department_abbr, signing_data):
    """添加或更新巡檢人員核簽資料檔
    
    Args:
        user_id (int): SysUser表的ID
        user_name (str): 用戶姓名
        user_id_str (str): 用戶ID字符串
        department_abbr (str): 部門縮寫
        signing_data (dict): 核簽資料
        
    Returns:
        bool: 是否成功
    """
    # 檢查是否已存在記錄
    existing_query = 'SELECT ID FROM [巡檢人員核簽資料檔] WHERE [巡檢人ID] = ?'
    existing = execute_query(existing_query, (user_id_str,), fetchone=True)
    
    if existing:
        # 更新現有記錄
        update_query = '''
            UPDATE [巡檢人員核簽資料檔] SET
                [巡檢人姓名] = ?, [部門] = ?, [部門縮寫] = ?,
                [主管姓名] = ?, [主管ID] = ?, [課長姓名] = ?, [課長ID] = ?,
                [廠工安人員1] = ?, [廠工安人員1ID] = ?, [廠PSM專人姓名] = ?, [廠PSM專人ID] = ?,
                [廠長姓名] = ?, [廠長ID] = ?, [工安主管姓名] = ?, [工安主管ID] = ?,
                [工安高專姓名] = ?, [工安高專ID] = ?, [廠] = ?, [課] = ?,
                [職稱] = ?, [第二部門] = ?
            WHERE [巡檢人ID] = ?
        '''
        params = (
            user_name, department_abbr, department_abbr,
            signing_data.get('supervisorName', ''), signing_data.get('supervisorID', ''),
            signing_data.get('sectionChiefName', ''), signing_data.get('sectionChiefID', ''),
            signing_data.get('safetyOfficer1', ''), signing_data.get('safetyOfficer1ID', ''),
            signing_data.get('psmSpecialistName', ''), signing_data.get('psmSpecialistID', ''),
            signing_data.get('factoryManagerName', ''), signing_data.get('factoryManagerID', ''),
            signing_data.get('safetySupervisorName', ''), signing_data.get('safetySupervisorID', ''),
            signing_data.get('safetySpecialistName', ''), signing_data.get('safetySpecialistID', ''),
            signing_data.get('factory', ''), signing_data.get('section', ''),
            signing_data.get('jobTitle', ''), signing_data.get('secondDepartment', ''),
            user_id_str
        )
        execute_query(update_query, params, commit=True)
    else:
        # 插入新記錄
        insert_query = '''
            INSERT INTO [巡檢人員核簽資料檔] (
                [巡檢人姓名], [巡檢人ID], [部門], [部門縮寫],
                [主管姓名], [主管ID], [課長姓名], [課長ID],
                [廠工安人員1], [廠工安人員1ID], [廠PSM專人姓名], [廠PSM專人ID],
                [廠長姓名], [廠長ID], [工安主管姓名], [工安主管ID],
                [工安高專姓名], [工安高專ID], [廠], [課],
                [職稱], [第二部門]
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        '''
        params = (
            user_name, user_id_str, department_abbr, department_abbr,
            signing_data.get('supervisorName', ''), signing_data.get('supervisorID', ''),
            signing_data.get('sectionChiefName', ''), signing_data.get('sectionChiefID', ''),
            signing_data.get('safetyOfficer1', ''), signing_data.get('safetyOfficer1ID', ''),
            signing_data.get('psmSpecialistName', ''), signing_data.get('psmSpecialistID', ''),
            signing_data.get('factoryManagerName', ''), signing_data.get('factoryManagerID', ''),
            signing_data.get('safetySupervisorName', ''), signing_data.get('safetySupervisorID', ''),
            signing_data.get('safetySpecialistName', ''), signing_data.get('safetySpecialistID', ''),
            signing_data.get('factory', ''), signing_data.get('section', ''),
            signing_data.get('jobTitle', ''), signing_data.get('secondDepartment', '')
        )
        execute_query(insert_query, params, commit=True)
    
    return True

def get_signing_data_by_user_id(user_id_str):
    """獲取用戶的核簽資料
    
    Args:
        user_id_str (str): 用戶ID字符串
        
    Returns:
        dict: 核簽資料或None
    """
    query = 'SELECT * FROM [巡檢人員核簽資料檔] WHERE [巡檢人ID] = ?'
    return execute_query(query, (user_id_str,), fetchone=True)

def delete_signing_data_by_user_id(user_id_str):
    """刪除用戶的核簽資料
    
    Args:
        user_id_str (str): 用戶ID字符串
        
    Returns:
        bool: 是否成功刪除
    """
    try:
        query = 'DELETE FROM [巡檢人員核簽資料檔] WHERE [巡檢人ID] = ?'
        execute_query(query, (user_id_str,), commit=True)
        return True
    except Exception:
        return False

def validate_user_data_consistency(user_id):
    """驗證用戶在兩張表中的資料一致性
    
    Args:
        user_id (int): 用戶ID
        
    Returns:
        dict: 驗證結果，包含是否一致和具體問題
    """
    result = {
        'is_consistent': True,
        'issues': []
    }
    
    try:
        # 獲取SysUser表的資料
        sys_user = get_user_by_id(user_id)
        if not sys_user:
            result['is_consistent'] = False
            result['issues'].append('SysUser表中找不到該用戶')
            return result
        
        # 獲取核簽資料表的資料
        signing_data = get_signing_data_by_user_id(sys_user.get('UserID'))
        if not signing_data:
            # 沒有核簽資料不算錯誤，因為這是可選的
            return result
        
        # 檢查姓名是否一致
        if sys_user.get('UserName') != signing_data.get('巡檢人姓名'):
            result['is_consistent'] = False
            result['issues'].append(f"姓名不一致: SysUser={sys_user.get('UserName')}, 核簽資料={signing_data.get('巡檢人姓名')}")
        
        # 檢查用戶ID是否一致
        if sys_user.get('UserID') != signing_data.get('巡檢人ID'):
            result['is_consistent'] = False
            result['issues'].append(f"用戶ID不一致: SysUser={sys_user.get('UserID')}, 核簽資料={signing_data.get('巡檢人ID')}")
        
        # 檢查部門是否一致
        if sys_user.get('Department') != signing_data.get('部門縮寫'):
            result['is_consistent'] = False
            result['issues'].append(f"部門不一致: SysUser={sys_user.get('Department')}, 核簽資料={signing_data.get('部門縮寫')}")
        
    except Exception as e:
        result['is_consistent'] = False
        result['issues'].append(f"驗證過程中發生錯誤: {str(e)}")
    
    return result

def fix_user_data_consistency(user_id):
    """修復用戶資料一致性問題
    
    Args:
        user_id (int): 用戶ID
        
    Returns:
        bool: 是否成功修復
    """
    try:
        # 獲取SysUser表的資料（作為主要資料來源）
        sys_user = get_user_by_id(user_id)
        if not sys_user:
            return False
        
        # 獲取核簽資料
        signing_data = get_signing_data_by_user_id(sys_user.get('UserID'))
        if not signing_data:
            return True  # 沒有核簽資料，無需修復
        
        # 使用SysUser表的資料更新核簽資料表
        update_query = '''
            UPDATE [巡檢人員核簽資料檔] SET
                [巡檢人姓名] = ?, [巡檢人ID] = ?, [部門] = ?, [部門縮寫] = ?
            WHERE [巡檢人ID] = ?
        '''
        params = (
            sys_user.get('UserName'),
            sys_user.get('UserID'),
            sys_user.get('Department', ''),
            sys_user.get('Department', ''),
            sys_user.get('UserID')
        )
        execute_query(update_query, params, commit=True)
        
        return True
    except Exception:
        return False

def add_user(user_data):
    """添加新用戶（同時處理SysUser和巡檢人員核簽資料檔兩張表）
    
    Args:
        user_data (dict): 用戶數據，包含以下字段：
            - UserName: 用戶名稱
            - UserID: 用戶ID
            - EngName: 英文名稱
            - Email: 電子郵件
            - Password: 密碼
            - PriorityLevel: 優先級別
            - Position: 職位
            - Shift: 班次
            - Department: 部門
            - Remark: 備註
            - Shifts: 班次代碼
            - isAtWork: 在職狀態
            - signingData: 核簽資料（可選）
        
    Returns:
        dict: 新建用戶信息或 None（如果失敗）
        
    Raises:
        Exception: 如果用戶創建失敗
    """
    # 檢查用戶是否已存在
    existing_user = get_user_by_user_id(user_data.get('UserID'))
    if existing_user:
        return None
    
    # 加密密碼
    if user_data.get('Password'):
        hashed_password = bcrypt.hashpw(user_data['Password'].encode('utf-8'), bcrypt.gensalt())
        user_data['Password'] = hashed_password.decode('utf-8')
    
    # 插入新用戶到SysUser表
    query = '''
        INSERT INTO SysUser (
            UserName, UserID, EngName, Email, Password, 
            PriorityLevel, Position, Shift, Department, Remark, Shifts, 
            CreateDate, IsAtWork
        ) 
        VALUES (
            ?, ?, ?, ?, ?, 
            ?, ?, ?, ?, ?, ?, 
            GETDATE(), ?
        )
    '''
    insert_params = (
        user_data.get('UserName'),
        user_data.get('UserID'), 
        user_data.get('EngName'), 
        user_data.get('Email'), 
        user_data.get('Password'),
        user_data.get('PriorityLevel', 1), 
        user_data.get('Position'), 
        user_data.get('Shift'), 
        user_data.get('Department'), 
        user_data.get('Remark'),
        user_data.get('Shifts'),
        1 if user_data.get('isAtWork', True) else 0
    )

    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(query, insert_params)
        
        # 立即在同一游標上執行 SELECT SCOPE_IDENTITY()
        id_query = "SELECT SCOPE_IDENTITY() AS NewID"
        cur.execute(id_query)
        result_row = cur.fetchone()
        
        if result_row and result_row.NewID is not None:
            new_user_id = result_row.NewID
        else:
            # 如果 SCOPE_IDENTITY 失敗，嘗試通過 UserID 查詢新用戶
            new_user = get_user_by_user_id(user_data.get('UserID'))
            if new_user:
                new_user_id = new_user.get('ID')
            else:
                raise Exception("無法獲取新用戶的 ID (SCOPE_IDENTITY failed 且無法通過 UserID 查詢)")
        
        conn.commit() # 提交 INSERT
        
        # 處理核簽資料（如果提供）
        signing_data = user_data.get('signingData')
        if signing_data:
            try:
                add_signing_data(
                    new_user_id,
                    user_data.get('UserName'),
                    user_data.get('UserID'),
                    user_data.get('Department', ''),
                    signing_data
                )
            except Exception as e:
                # 如果核簽資料插入失敗，記錄錯誤但不回滾主用戶創建
                current_app.logger.warning(f"核簽資料插入失敗: {str(e)}")
        
        # 根據 ID 獲取完整的用戶信息（包含核簽資料）
        new_user = get_user_with_signing_data(new_user_id)
        if not new_user:
            raise Exception("無法獲取新用戶的信息")
        return new_user

    except Exception as e:
        # 如果出錯，嘗試回滾 (雖然 INSERT 可能已提交)
        if conn:
            conn.rollback()
        raise Exception(f"添加用戶失敗: {str(e)}")
    finally:
        if cur:
            cur.close()

def get_user_with_signing_data(user_id):
    """獲取用戶信息及其核簽資料
    
    Args:
        user_id (int): 用戶ID
        
    Returns:
        dict: 包含用戶信息和核簽資料的字典
    """
    user = get_user_by_id(user_id)
    if not user:
        return None
    
    # 獲取核簽資料
    signing_data = get_signing_data_by_user_id(user.get('UserID'))
    if signing_data:
        # 將核簽資料添加到用戶信息中
        user.update({
            'supervisorName': signing_data.get('主管姓名', ''),
            'supervisorID': signing_data.get('主管ID', ''),
            'sectionChiefName': signing_data.get('課長姓名', ''),
            'sectionChiefID': signing_data.get('課長ID', ''),
            'safetyOfficer1': signing_data.get('廠工安人員1', ''),
            'safetyOfficer1ID': signing_data.get('廠工安人員1ID', ''),
            'psmSpecialistName': signing_data.get('廠PSM專人姓名', ''),
            'psmSpecialistID': signing_data.get('廠PSM專人ID', ''),
            'factoryManagerName': signing_data.get('廠長姓名', ''),
            'factoryManagerID': signing_data.get('廠長ID', ''),
            'safetySupervisorName': signing_data.get('工安主管姓名', ''),
            'safetySupervisorID': signing_data.get('工安主管ID', ''),
            'safetySpecialistName': signing_data.get('工安高專姓名', ''),
            'safetySpecialistID': signing_data.get('工安高專ID', ''),
            'factory': signing_data.get('廠', ''),
            'section': signing_data.get('課', ''),
            'departmentAbbr': signing_data.get('部門縮寫', ''),
            'jobTitle': signing_data.get('職稱', ''),
            'secondDepartment': signing_data.get('第二部門', '')
        })
    
    return user

def get_all_users_with_signing_data():
    """獲取所有用戶及其核簽資料
    
    Returns:
        list: 包含用戶信息和核簽資料的用戶列表
    """
    users = get_all_users()
    result = []
    
    for user in users:
        user_with_signing = get_user_with_signing_data(user['ID'])
        if user_with_signing:
            result.append(user_with_signing)
    
    return result

def update_user(user_id, user_data):
    """更新用戶信息（同時處理SysUser和巡檢人員核簽資料檔兩張表）
    
    Args:
        user_id (int): 用戶ID
        user_data (dict): 要更新的用戶數據
        
    Returns:
        dict: 更新後的用戶信息或 None（如果失敗）
        
    Raises:
        Exception: 如果用戶更新失敗
    """
    # 檢查用戶是否存在
    existing_user = get_user_by_id(user_id)
    if not existing_user:
        return None
    
    # 如果提供了新密碼，則加密
    if user_data.get('Password'):
        hashed_password = bcrypt.hashpw(user_data['Password'].encode('utf-8'), bcrypt.gensalt())
        user_data['Password'] = hashed_password.decode('utf-8')
    
    # 分離SysUser字段和核簽資料
    sys_user_fields = {
        'UserName', 'UserID', 'EngName', 'Email', 'Password', 
        'PriorityLevel', 'Position', 'Shift', 'Department', 
        'Remark', 'Shifts', 'isAtWork'
    }
    
    signing_data = user_data.get('signingData', {})
    
    # 構建SysUser更新查詢
    set_clauses = []
    params = []
    
    for key, value in user_data.items():
        if value is not None and key in sys_user_fields and key != 'ID':
            if key == 'isAtWork':
                set_clauses.append("IsAtWork = ?")
                params.append(1 if value else 0)
            else:
                set_clauses.append(f"{key} = ?")
                params.append(value)
    
    # 添加更新時間
    if set_clauses:
        set_clauses.append("UpdateDate = GETDATE()")
        params.append(user_id)
        
        query = f'''
            UPDATE SysUser 
            SET {', '.join(set_clauses)} 
            WHERE ID = ?
        '''
        execute_query(query, params, commit=True)
    
    # 更新核簽資料（如果提供）
    if signing_data:
        try:
            current_user = get_user_by_id(user_id)
            if current_user:
                add_signing_data(
                    user_id,
                    user_data.get('UserName', current_user.get('UserName')),
                    user_data.get('UserID', current_user.get('UserID')),
                    user_data.get('Department', current_user.get('Department', '')),
                    signing_data
                )
        except Exception as e:
            # 記錄錯誤但不回滾主用戶更新
            print(f"核簽資料更新失敗: {str(e)}")
    
    # 返回更新後的完整用戶信息（包含核簽資料）
    try:
        updated_user = get_user_with_signing_data(user_id)
        return updated_user
    except Exception as e:
        raise Exception(f"更新用戶失敗: {str(e)}")

def get_user_by_id(user_id):
    """通過 ID 查詢用戶
    
    Args:
        user_id (int): 用戶 ID
        
    Returns:
        dict: 用戶信息或 None（如果不存在）
    """
    query = 'SELECT * FROM SysUser WHERE ID = ?'
    params = (user_id,)
    return execute_query(query, params, fetchone=True)

def get_user_by_user_id(user_id):
    """通過 UserID 查詢用戶
    
    Args:
        user_id (str): 用戶 UserID
        
    Returns:
        dict: 用戶信息或 None（如果不存在）
    """
    query = 'SELECT * FROM SysUser WHERE UserID = ?'
    params = (user_id,)
    return execute_query(query, params, fetchone=True)

def get_all_users():
    """獲取所有用戶
    
    Returns:
        list: 用戶列表
    """
    query = 'SELECT * FROM SysUser ORDER BY ID'
    return execute_query(query)

def delete_user(user_id):
    """刪除用戶（同時刪除SysUser和巡檢人員核簽資料檔兩張表的記錄）
    
    Args:
        user_id (int): 用戶 ID
        
    Returns:
        bool: 是否成功刪除
    """
    try:
        # 首先獲取用戶信息以獲得UserID
        user = get_user_by_id(user_id)
        if not user:
            return False
        
        user_id_str = user.get('UserID')
        
        # 刪除核簽資料
        if user_id_str:
            delete_signing_data_by_user_id(user_id_str)
        
        # 刪除SysUser記錄
        query = 'DELETE FROM SysUser WHERE ID = ?'
        params = (user_id,)
        execute_query(query, params, commit=True)
        
        return True
    except Exception:
        return False

def verify_password(user_id, password):
    """驗證用戶密碼
    
    Args:
        user_id (str): 用戶 UserID
        password (str): 待驗證的密碼
        
    Returns:
        dict: 用戶信息（如果驗證成功）或 None
    """
    user = get_user_by_user_id(user_id)
    
    if not user or not user.get('Password'):
        return None
    
    is_valid = bcrypt.checkpw(
        password.encode('utf-8'), 
        user['Password'].encode('utf-8')
    )
    
    if is_valid:
        return user
    
    return None

def check_priority_level(user_id, required_level=1):
    """檢查用戶是否具有指定優先級別
    
    Args:
        user_id (int): 用戶 ID
        required_level (int): 所需的優先級別
        
    Returns:
        bool: 是否具有所需優先級別
    """
    user = get_user_by_id(user_id)
    
    if user and (user.get('PriorityLevel') or 0) >= required_level:
        return True
    
    return False

def set_user_work_status(user_id, is_at_work):
    """設置用戶工作狀態
    
    Args:
        user_id (int): 用戶 ID
        is_at_work (bool): 是否在工作
        
    Returns:
        bool: 是否成功設置
    """
    query = 'UPDATE SysUser SET IsAtWork = ?, UpdateDate = GETDATE() WHERE ID = ?'
    params = (1 if is_at_work else 0, user_id)
    
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(query, params)
        affected_rows = cur.rowcount  # 獲取受影響的行數
        conn.commit()
        
        # 檢查是否有行被更新
        if affected_rows > 0:
            return True
        else:
            # 沒有找到對應的用戶ID
            return False
            
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Database update error in set_user_work_status: {e}")
        return False
    finally:
        if cur:
            cur.close()
