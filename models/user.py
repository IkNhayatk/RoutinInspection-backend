import bcrypt
# 使用絕對路徑導入
from db import execute_query, get_db

def add_user(user_data):
    """添加新用戶
    
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
    
    # 插入新用戶
    query = '''
        INSERT INTO SysUser (
            UserName, UserID, EngName, Email, Password, 
            PriorityLevel, Position, Shift, Department, Remark, Shifts, 
            CreateDate, IsAtWork
        ) 
        VALUES (
            ?, ?, ?, ?, ?, 
            ?, ?, ?, ?, ?, ?, 
            GETDATE(), 0
        )
    '''
    insert_params = (
        user_data.get('UserName'),
        user_data.get('UserID'), 
        user_data.get('EngName'), 
        user_data.get('Email'), 
        user_data.get('Password'),
        user_data.get('PriorityLevel', 0), 
        user_data.get('Position'), 
        user_data.get('Shift'), 
        user_data.get('Department'), 
        user_data.get('Remark'),
        user_data.get('Shifts'),
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
        
        # 根據 ID 獲取完整的用戶信息
        new_user = get_user_by_id(new_user_id)
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

def update_user(user_id, user_data):
    """更新用戶信息
    
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
    
    # 構建更新查詢
    set_clauses = []
    params = []
    
    for key, value in user_data.items():
        if value is not None and key != 'ID':  # 排除ID字段
            set_clauses.append(f"{key} = ?")
            params.append(value)
    
    # 添加更新時間
    set_clauses.append("UpdateDate = GETDATE()")
    
    # 添加用戶ID參數
    params.append(user_id)
    
    query = f'''
        UPDATE SysUser 
        SET {', '.join(set_clauses)} 
        WHERE ID = ? 
        SELECT * FROM SysUser WHERE ID = ?
    '''
    
    # 再次添加用戶ID參數用於SELECT
    params.append(user_id)
    
    try:
        user = execute_query(query, params, commit=True, fetchone=True)
        return user
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
    """刪除用戶
    
    Args:
        user_id (int): 用戶 ID
        
    Returns:
        bool: 是否成功刪除
    """
    query = 'DELETE FROM SysUser WHERE ID = ?'
    params = (user_id,)
    
    try:
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
    
    if user and user.get('PriorityLevel', 0) >= required_level:
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
