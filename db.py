import pyodbc
from flask import current_app, g

def get_db():
    """取得資料庫連接
    
    如果連接尚未在當前應用上下文中建立，則創建一個新的連接
    
    Returns:
        pyodbc.Connection: 資料庫連接物件
    """
    if 'db' not in g:
        # 從當前應用配置中獲取資料庫連接參數
        db_driver = current_app.config.get('DB_DRIVER')
        db_host = current_app.config.get('DB_HOST')
        db_name = current_app.config.get('DB_NAME')
        db_user = current_app.config.get('DB_USER')
        # 允許 DB_PASSWORD 為空字串，但不能是 None (未設定)
        db_password = current_app.config.get('DB_PASSWORD') 
        trust_cert = current_app.config.get('DB_TRUST_SERVER_CERTIFICATE', False) # 從配置讀取，預設 False

        # 檢查必要的配置是否存在
        # db_password 可以是空字串，所以檢查它是否為 None
        if not all([db_driver, db_host, db_name, db_user, db_password is not None]):
            current_app.logger.error("CRITICAL: Database connection parameters (DRIVER, HOST, NAME, USER, PASSWORD) are not fully configured.")
            raise ValueError("Database connection parameters are not fully configured.")

        connection_string_parts = [
            f"DRIVER={db_driver}",
            f"SERVER={db_host}",
            f"DATABASE={db_name}",
            f"UID={db_user}",
            f"PWD={db_password}"
        ]
        
        if trust_cert:
            connection_string_parts.append("TrustServerCertificate=yes")
        # 如果 trust_cert 為 False，則不添加 TrustServerCertificate=yes，
        # 讓 pyodbc/驅動程式使用其預設行為 (通常是嘗試驗證憑證)。

        connection_string = ";".join(connection_string_parts)
        # 確保連接字串以分號結尾（如果 pyodbc 或特定驅動程式需要）
        if not connection_string.endswith(';'):
            connection_string += ';'
            
        current_app.logger.debug(f"Attempting to connect with DSN built from configuration.")
        try:
            g.db = pyodbc.connect(connection_string)
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            current_app.logger.error(f"CRITICAL: Database connection failed. SQLSTATE: {sqlstate}. Error: {ex}")
            # 可以根據 sqlstate 進一步處理特定錯誤，例如登入失敗、找不到伺服器等
            raise ValueError(f"Database connection failed: {ex}") # 重新拋出更通用的異常或自訂異常
    
    return g.db

def close_db(e=None):
    """關閉資料庫連接
    
    如果存在，則關閉當前上下文中的資料庫連接
    
    Args:
        e: 可選的異常物件
    """
    db = g.pop('db', None)
    
    if db is not None:
        try:
            db.close()
        except pyodbc.Error as ex:
            current_app.logger.warning(f"Warning: Error while closing the database connection: {ex}")


def init_app(app):
    """初始化應用程式的資料庫連接
    
    註冊資料庫相關的事件處理器
    
    Args:
        app: Flask 應用程式實例
    """
    app.teardown_appcontext(close_db)
    # init_db(app) # 通常 init_db 是用來創建表結構的，如果只是初始化連接，這一行可能不需要
                   # 或者如果 init_db 有其他用途（如檢查連接），則保留

def execute_query(query, params=None, commit=False, fetchone=False):
    """執行 SQL 查詢並返回結果
    
    Args:
        query (str): SQL 查詢語句
        params (tuple, optional): 查詢參數。默認為 None
        commit (bool, optional): 是否提交事務。默認為 False
        fetchone (bool, optional): 是否只返回一個結果。默認為 False
        
    Returns:
        list/dict: 查詢結果
        
    Raises:
        Exception: 執行查詢時發生錯誤
    """
    conn = get_db() # 如果 get_db 拋出異常 (例如配置不完整或連接失敗)，這裡會中斷
    cur = None # 初始化 cur 以確保 finally 區塊中可用
    try:
        cur = conn.cursor()
        cur.execute(query, params or ())
        
        result = None # 初始化 result
        if fetchone:
            row = cur.fetchone()
            if row:
                columns = [column[0] for column in cur.description]
                result = dict(zip(columns, row))
        else:
            # 即使沒有結果，也應該返回空列表而不是 None，以保持一致性
            rows = cur.fetchall()
            columns = [column[0] for column in cur.description] # 即使 rows 為空，description 仍可用
            result = [dict(zip(columns, row)) for row in rows]
            
        if commit:
            conn.commit()
            
        return result
    except pyodbc.Error as ex: # 更具體地捕獲 pyodbc 錯誤
        current_app.logger.error(f"Database query error: {ex}. Query: {query[:200]}...") # 只記錄查詢的前200字符
        if conn and commit: # 只有在嘗試提交時才回滾
            try:
                conn.rollback()
            except pyodbc.Error as rb_ex:
                current_app.logger.error(f"Database rollback failed: {rb_ex}")
        raise # 重新拋出原始的 pyodbc.Error，或者一個更通用的自訂錯誤
    finally:
        if cur:
            try:
                cur.close()
            except pyodbc.Error as ex:
                 current_app.logger.warning(f"Warning: Error while closing cursor: {ex}")


def init_db(app): # 這個函數的用途似乎是創建表，如果僅用於初始化，可能不需要
    """初始化數據庫表結構 (如果需要的話)"""
    # 根據您的應用邏輯，決定此函數的確切行為。
    # 如果您是使用資料庫遷移工具 (如 Alembic)，則此函數可能不需要執行 DDL。
    # 如果您希望在應用啟動時檢查/創建表，則保留此邏輯。
    with app.app_context():
        try:
            db = get_db() # 確保可以連接
            current_app.logger.info("Database connection successful during init_db.")
            # 以下是您原有的邏輯，如果不再需要，可以移除或修改
            # cursor = db.cursor()
            # try:
            #     # 不再創建 users 表，使用現有的 SysUser 表
            #     # 不再創建 forms 表，使用現有的 TableManager 表
            #     db.commit() # 如果沒有執行任何修改操作，這個 commit 可能不需要
            # except Exception as e:
            #     db.rollback()
            #     raise e
            # finally:
            #     if cursor: cursor.close()
        except ValueError as ve: # 捕獲 get_db 中因配置問題拋出的 ValueError
             current_app.logger.error(f"Failed to initialize database (ValueError in get_db): {ve}")
        except pyodbc.Error as ex: # 捕獲 get_db 中因連接失敗拋出的 pyodbc.Error
             current_app.logger.error(f"Failed to initialize database (pyodbc.Error in get_db): {ex}")