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
        connection_string = (
            f"DRIVER={current_app.config['DB_DRIVER']};"
            f"SERVER={current_app.config['DB_HOST']};"
            f"DATABASE={current_app.config['DB_NAME']};"
            f"UID={current_app.config['DB_USER']};"
            f"PWD={current_app.config['DB_PASSWORD']};"
            f"TrustServerCertificate=yes;"
        )
        g.db = pyodbc.connect(connection_string)
    
    return g.db

def close_db(e=None):
    """關閉資料庫連接
    
    如果存在，則關閉當前上下文中的資料庫連接
    
    Args:
        e: 可選的異常物件
    """
    db = g.pop('db', None)
    
    if db is not None:
        db.close()

def init_app(app):
    """初始化應用程式的資料庫連接
    
    註冊資料庫相關的事件處理器
    
    Args:
        app: Flask 應用程式實例
    """
    app.teardown_appcontext(close_db)
    init_db(app)

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
    conn = get_db()
    cur = conn.cursor()
    result = None
    
    try:
        cur.execute(query, params or ())
        
        if fetchone:
            row = cur.fetchone()
            if row:
                # 將結果轉換為字典
                columns = [column[0] for column in cur.description]
                result = dict(zip(columns, row))
        else:
            rows = cur.fetchall()
            if rows:
                # 將結果轉換為字典列表
                columns = [column[0] for column in cur.description]
                result = [dict(zip(columns, row)) for row in rows]
            else:
                result = []
            
        if commit:
            conn.commit()
            
        return result
    except Exception as e:
        if commit: # 只有在嘗試提交時才回滾
            conn.rollback()
        raise e
    finally:
        cur.close()

def init_db(app):
    """初始化數據庫表結構"""
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        try:
            # 不再創建 users 表，使用現有的 SysUser 表
            # 不再創建 forms 表，使用現有的 TableManager 表
            
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            cursor.close()
