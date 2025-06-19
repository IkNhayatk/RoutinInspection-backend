import json
import logging
from flask import abort, current_app
from db import get_db

def add_form(form_data):
    """添加新表單定義到 TableManager"""
    db = get_db()
    cursor = db.cursor()
    try:
        # 處理 formJson: 如果是字串則解析，取得 SchemaContent
        form_json = form_data.get('formJson')
        if isinstance(form_json, str):
            try:
                form_json = json.loads(form_json)
            except json.JSONDecodeError:
                form_json = {}
        
        # 使用 formJson 或 items 作為 SchemaContent
        schema_content = form_json or form_data.get('items', {})
        # 確保 schema_content 是有效的 JSON 物件或列表
        if not isinstance(schema_content, (dict, list)):
             schema_content = {} # 或其他預設值
        schema_content_str = json.dumps(schema_content)
        
        cursor.execute("""
            INSERT INTO TableManager (TableName, DisplayName, SchemaContent, ItemsCnt)
            VALUES (?, ?, ?, ?)
        """, (form_data['formIdentifier'], form_data['formDisplayName'], schema_content_str, form_data.get('itemsCnt', 0)))
        db.commit()
        # 使用 SELECT @@IDENTITY 來獲取新插入的 ID
        cursor.execute("SELECT @@IDENTITY AS id")
        form_id = int(cursor.fetchone()[0])
        current_app.logger.info(f"Added form definition with ID: {form_id}")
        
        # 創建對應的資料表
        from .form_schema import create_form_table
        try:
            create_result = create_form_table(form_data)
            if not create_result.get("success", False):
                db.rollback()
                current_app.logger.error(f"Failed to create table for form ID {form_id}: {create_result.get('message', 'Unknown error')}")
                abort(500, description=f"Failed to create table: {create_result.get('message', 'Unknown error')}")
            table_name = create_result.get("table_name", "")
        except Exception as e:
            db.rollback()
            current_app.logger.error(f"Error creating table for form ID {form_id}: {str(e)}")
            abort(500, description=f"Error creating table: {str(e)}")
        
        return {
            "id": form_id,
            "success": True,
            "formIdentifier": form_data['formIdentifier'],
            "formDisplayName": form_data['formDisplayName'],
            "table_name": table_name
        }
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error adding form definition: {str(e)}")
        abort(500, description=f"Error adding form definition: {str(e)}")
    finally:
        if cursor:
            cursor.close()

def get_all_forms(page=1, limit=10):
    """獲取所有表單定義，支援分頁，排除TestMode為3的資料"""
    db = get_db()
    cursor = db.cursor()
    try:
        offset = (page - 1) * limit
        # 確保選取的欄位順序和索引是正確的
        cursor.execute("""
            SELECT TableManagerId, TableName, SchemaContent, TableName, DisplayName, TestMode 
            FROM TableManager 
            WHERE TestMode != 3 
            ORDER BY TableManagerId 
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, (offset, limit))
        forms = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) FROM TableManager WHERE TestMode != 3")
        total = cursor.fetchone()[0]
        
        # 修正索引以匹配 SELECT 查詢
        result_forms = []
        for row in forms:
             form_json_str = row[2]
             form_json_obj = None
             try:
                 if form_json_str:
                      form_json_obj = json.loads(form_json_str)
             except json.JSONDecodeError:
                 current_app.logger.warning(f"Could not parse SchemaContent for form ID {row[0]}")
                 form_json_obj = {} # 或者 None，取決於前端期望

             result_forms.append({
                 "id": row[0], 
                 "dbName": row[3], # 使用 TableName 作為 dbName
                 "eFormName": row[4], # 使用 DisplayName 作為 eFormName
                 "mode": row[5], 
                 "formJson": form_json_obj # 返回解析後的 JSON 物件
             })

        return {
            "forms": result_forms,
            "total": total
        }
    except Exception as e:
        current_app.logger.error(f"Error getting all form definitions: {str(e)}")
        abort(500, description=f"Error retrieving form definitions: {str(e)}")
    finally:
        if cursor:
            cursor.close()

def get_form_by_id(form_id):
    """根據ID獲取單個表單定義，排除TestMode為3的資料"""
    db = get_db()
    cursor = db.cursor()
    try:
        # 確保選取的欄位順序和索引是正確的
        cursor.execute("""
            SELECT TableManagerId, TableName, SchemaContent, TableName, DisplayName, TestMode 
            FROM TableManager 
            WHERE TableManagerId = ? AND TestMode != 3
        """, (form_id,))
        form = cursor.fetchone()
        if form:
            form_json_str = form[2]
            form_json_obj = None
            try:
                if form_json_str:
                    form_json_obj = json.loads(form_json_str)
            except json.JSONDecodeError:
                current_app.logger.warning(f"Could not parse SchemaContent for form ID {form[0]}")
                form_json_obj = {} # 或 None

            # 返回與 get_all_forms 類似的結構以便前端使用
            return {
                "id": form[0], 
                "dbName": form[3], # TableName
                "eFormName": form[4], # DisplayName
                "mode": form[5],
                "formJson": form_json_obj # Parsed JSON
            }
        return None # 如果找不到表單
    except Exception as e:
        current_app.logger.error(f"Error getting form definition by ID {form_id}: {str(e)}")
        abort(500, description=f"Error retrieving form definition: {str(e)}")
    finally:
        if cursor:
            cursor.close()

def update_form(form_id, form_data):
    """更新 TableManager 中的表單定義數據"""
    db = get_db()
    cursor = db.cursor()
    try:
        # 處理 formJson: 如果是字串則解析，取得 SchemaContent
        form_json = form_data.get('formJson')
        if isinstance(form_json, str):
            try:
                form_json = json.loads(form_json)
            except json.JSONDecodeError:
                form_json = {}
        else:
            # 確保 form_json 是字典或列表，否則設為空字典
            form_json = form_json if isinstance(form_json, (dict, list)) else {}
        
        # 使用 formJson 作為 SchemaContent
        schema_content_str = json.dumps(form_json)
        
        cursor.execute("""
            UPDATE TableManager
            SET TableName = ?, DisplayName = ?, SchemaContent = ?, ItemsCnt = ?
            WHERE TableManagerId = ? AND TestMode != 3
        """, (
            form_data.get('formIdentifier', ''), 
            form_data.get('formDisplayName', ''), 
            schema_content_str, 
            form_data.get('itemsCnt', 0), 
            form_id
        ))
        db.commit()
        
        if cursor.rowcount > 0:
            current_app.logger.info(f"Updated form definition for ID: {form_id}")
            # 返回更新後的部分數據，或者可以重新查詢一次以獲取完整數據
            return {"id": form_id, "success": True, **form_data} 
        else:
            # 檢查表單是否存在但 TestMode=3 或 ID 不存在
            cursor.execute("SELECT COUNT(*) FROM TableManager WHERE TableManagerId = ?", (form_id,))
            exists = cursor.fetchone()[0] > 0
            if not exists:
                 current_app.logger.warning(f"Attempted to update non-existent form definition ID: {form_id}")
                 abort(404, description=f"Form definition with ID {form_id} not found.")
            else:
                 current_app.logger.warning(f"Attempted to update form definition ID {form_id} which might have TestMode=3.")
                 # 可以選擇返回 None 或特定的錯誤訊息
                 return None # 或 abort(403, ...)
            
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error updating form definition ID {form_id}: {str(e)}")
        abort(500, description=f"Error updating form definition: {str(e)}")
    finally:
        if cursor:
            cursor.close()

def delete_form(form_id):
    """從 TableManager 刪除表單定義 (邏輯刪除，設定 TestMode=3 並重新命名資料表)"""
    db = get_db()
    cursor = db.cursor()
    try:
        # 1. 先獲取目前的表單資訊並進行 trim 處理
        cursor.execute("SELECT TableName FROM TableManager WHERE TableManagerId = ? AND TestMode != 3", (form_id,))
        result = cursor.fetchone()
        if not result:
            current_app.logger.warning(f"Attempted to delete non-existent or already deleted form definition ID: {form_id}")
            return False
        
        table_name = result[0].strip()  # 對表名進行 trim() 處理
        
        # 2. 生成新的表名（加上 'old' + 流水號），檢查衝突並遞增
        new_table_name = _generate_unique_table_name(cursor, table_name)
        
        # 3. 更新 TableManager 設定 TestMode=3 並更新 TableName
        cursor.execute("""
            UPDATE TableManager 
            SET TestMode = 3, TableName = ? 
            WHERE TableManagerId = ?
        """, (new_table_name, form_id))
        
        # 儲存 UPDATE 操作影響的行數
        update_rowcount = cursor.rowcount
        
        # 4. 重新命名實際的資料表
        try:
            # 檢查原始表是否存在
            cursor.execute("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = ? AND TABLE_SCHEMA = 'dbo'
            """, (table_name,))
            table_exists = cursor.fetchone()[0] > 0
            
            if table_exists:
                # 執行表名重新命名
                rename_sql = f"EXEC sp_rename '{table_name}', '{new_table_name}'"
                cursor.execute(rename_sql)
                current_app.logger.info(f"Renamed table from {table_name} to {new_table_name}")
            else:
                current_app.logger.warning(f"Table {table_name} does not exist, skipping rename")
        except Exception as rename_error:
            current_app.logger.error(f"Error renaming table {table_name} to {new_table_name}: {str(rename_error)}")
            # 即使重新命名失敗，我們也繼續進行邏輯刪除
        
        db.commit()
        
        # 使用儲存的 UPDATE 操作行數檢查
        if update_rowcount > 0:
            current_app.logger.info(f"Logically deleted form definition ID: {form_id}, renamed table to: {new_table_name}")
            return True
        else:
            current_app.logger.warning(f"No rows affected when deleting form definition ID: {form_id}")
            return False
            
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error logically deleting form definition ID {form_id}: {str(e)}")
        abort(500, description=f"Error deleting form definition: {str(e)}")
    finally:
        if cursor:
            cursor.close()

def _generate_unique_table_name(cursor, original_table_name):
    """生成唯一的表名，格式為：原名 + '_old' + 流水號"""
    counter = 1
    while True:
        new_table_name = f"{original_table_name}_old{counter}"
        
        # 檢查 TableManager 中是否已存在相同名稱
        cursor.execute("SELECT COUNT(*) FROM TableManager WHERE TableName = ?", (new_table_name,))
        manager_exists = cursor.fetchone()[0] > 0
        
        # 檢查實際資料表是否已存在
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = ? AND TABLE_SCHEMA = 'dbo'
        """, (new_table_name,))
        table_exists = cursor.fetchone()[0] > 0
        
        # 如果都不存在，就使用這個名稱
        if not manager_exists and not table_exists:
            return new_table_name
        
        # 如果存在衝突，流水號 +1 繼續檢查
        counter += 1
        
        # 防止無限循環，設定上限
        if counter > 9999:
            raise Exception(f"無法為表 {original_table_name} 生成唯一名稱，已達到最大嘗試次數")
    
    return new_table_name

def update_form_mode(form_id, mode):
    """更新表單定義的模式 (TestMode)"""
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("UPDATE TableManager SET TestMode = ? WHERE TableManagerId = ?", (mode, form_id))
        db.commit()
        if cursor.rowcount > 0:
            current_app.logger.info(f"Updated mode for form definition ID {form_id} to {mode}")
            return True
        else:
            current_app.logger.warning(f"Attempted to update mode for non-existent form definition ID: {form_id}")
            return False # ID 不存在
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error updating mode for form definition ID {form_id}: {str(e)}")
        abort(500, description=f"Error updating form mode: {str(e)}")
    finally:
        if cursor:
            cursor.close()

def search_department(code: str):
    """根據部門代碼 (DisplayName 前四碼) 搜尋表單定義"""
    if len(code) != 4:
        abort(400, description="Department code must be 4 characters")
    
    db = get_db()
    cursor = db.cursor()
    try:
        # 使用參數化查詢防止 SQL 注入
        # 注意: SUBSTR 在不同資料庫中可能不同 (例如 SQL Server 是 SUBSTRING)
        # 這裡假設是 SQLite 或類似語法
        # 對於 SQL Server: WHERE SUBSTRING(DisplayName, 1, 4) = ? AND TestMode != 3
        cursor.execute("""
            SELECT TableManagerId, TableName, DisplayName 
            FROM TableManager
            WHERE SUBSTRING(DisplayName, 1, 4) = ? AND TestMode != 3 
        """, (code,)) # 使用 SUBSTRING for SQL Server
        rows = cursor.fetchall()
        
        # 返回與 get_all_forms 類似的結構
        return [
            {
                "id": r[0],
                "dbName": r[1], # TableName
                "eFormName": r[2], # DisplayName
                # 可以考慮加入 mode 等其他需要的欄位
            }
            for r in rows
        ]
    except Exception as e:
        current_app.logger.error(f"Error searching department code '{code}': {str(e)}")
        abort(500, description=f"Error searching forms by department: {str(e)}")
    finally:
        if cursor:
            cursor.close()

