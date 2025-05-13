import json
import logging
from flask import abort, current_app
from db import get_db
from .form_utils import collect_items # 從 utils 導入 collect_items

# TODO: 將資料庫名稱設為可配置 (例如，從環境變數或設定檔讀取)
DB_NAME = 'RoutinInspection_dev' # 或 'RoutinInspection'

def create_form_table(form_data):
    """
    根據表單 JSON 建立新的 user_ 資料表。
    如果已存在同名資料表，會先刪除再重建。
    form_data 需包含:
    - formIdentifier: 表單識別符 (用作資料表名稱)
    - formJson: 表單 JSON 結構 (可以是字串或已解析的 dict)
    """
    db = get_db()
    cursor = db.cursor()
    
    form_identifier = form_data.get('formIdentifier')
    if not form_identifier:
        abort(400, description="Missing formIdentifier for table creation.")
    
    # 去除空白字符
    trimmed_identifier = form_identifier.strip()
    # 檢查是否已經包含 user_ 前綴
    if trimmed_identifier.startswith("user_"):
        table_name = trimmed_identifier
    else:
        table_name = f"user_{trimmed_identifier}"
    
    # 確保 formJson 是字典物件
    form_json = form_data.get('formJson')
    if isinstance(form_json, str):
        try:
            form_json = json.loads(form_json)
        except json.JSONDecodeError:
            abort(400, description="Invalid JSON in formJson for table creation.")
    
    if not isinstance(form_json, dict): # 確保解析後是字典
        abort(400, description="formJson must be a valid JSON object.")
    
    current_app.logger.info(f"Attempting to create table '{table_name}' in database '{DB_NAME}'")

    try:
        # 遞迴收集所有 ItemId
        item_ids = []
        collect_items(form_json.get('Elements', []), item_ids) # 從 Elements 開始收集
        
        if not item_ids:
            # 如果沒有 ItemId，可能不應該建立表，或者建立一個只有基礎欄位的表
            current_app.logger.warning(f"No items found in formJson for '{form_identifier}'. Creating table with base columns only.")
            # 可以選擇中止或繼續建立基礎表
            # abort(400, description="No items found in formJson, cannot create table structure.")

        # 檢查資料表是否已存在，如果存在則刪除 (危險操作，請謹慎)
        # 在生產環境中，可能需要更安全的策略，例如備份或遷移
        cursor.execute(f"IF OBJECT_ID(N'[dbo].[{table_name}]', N'U') IS NOT NULL DROP TABLE [dbo].[{table_name}]")
        current_app.logger.info(f"Dropped existing table '{table_name}' if it existed.")
        
        # 基礎欄位
        base_columns = [
            f"[{table_name}Id] [int] IDENTITY(1,1) NOT NULL",
            "[UserId] [int] NULL",
            "[PointInfoId] [int] NULL",
            "[TableName] [nchar](32) NULL", # 考慮是否仍需要此欄位
            "[ReviewerId] [int] NULL",
            "[ReviewerComment] [nchar](32) NULL",
            "[CheckDate] [datetime] NULL"
        ]
        
        # 動態 Item 欄位
        item_columns = []
        for item_id in item_ids:
            item_columns.append(f"[Item{item_id}] [nvarchar](max) NULL")
            item_columns.append(f"[Item{item_id}_Remark] [nvarchar](max) NULL")
            
        all_columns = base_columns + item_columns

        # 主鍵約束
        primary_key_constraint = f"""
         CONSTRAINT [PK_{table_name}] PRIMARY KEY CLUSTERED 
        (
            [{table_name}Id] ASC
        )WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
        """

        # 建立資料表 SQL
        create_table_sql = f"""
        CREATE TABLE [dbo].[{table_name}](
            {','.join(all_columns)}
            {primary_key_constraint}
        ) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
        """
        
        current_app.logger.debug(f"Executing CREATE TABLE SQL for {table_name}: {create_table_sql}")
        cursor.execute(create_table_sql)
        db.commit()
        
        current_app.logger.info(f"Successfully created table '{table_name}'")
        
        return {
            "success": True,
            "message": f"Table {table_name} created successfully.",
            "table_name": table_name
        }
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error creating table '{table_name}': {str(e)}")
        abort(500, description=f"Error creating table: {str(e)}")
    finally:
        if cursor:
            cursor.close()


def rename_and_update_form_table(old_form_identifier, new_form_identifier, form_json):
    """
    重新命名 user_ 資料表，並根據新的 formJson 更新其結構 (僅新增欄位)。
    如果舊表不存在，則嘗試更新新表名的結構。
    如果新表名已存在，則中止。
    """
    if not old_form_identifier or not new_form_identifier:
        abort(400, description="Old and new form identifiers are required for rename/update.")
    
    # 如果名稱未變更，只需更新結構
    if old_form_identifier == new_form_identifier:
        current_app.logger.info(f"Form identifier '{new_form_identifier}' unchanged, only updating schema.")
        return update_form_table_schema(new_form_identifier, form_json)

    db = get_db()
    # 注意：sp_rename 不完全支援事務，這裡分開處理
    
    old_table_name = f"user_{old_form_identifier}"
    new_table_name = f"user_{new_form_identifier}"
    
    current_app.logger.info(f"Attempting to rename table '{old_table_name}' to '{new_table_name}' in database '{DB_NAME}'")

    rename_success = False
    cursor = db.cursor()
    try:
        # 1. 檢查舊資料表是否存在
        cursor.execute(f"""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ? AND TABLE_CATALOG = ? 
        """, (old_table_name, DB_NAME))
        if not cursor.fetchone():
            current_app.logger.warning(f"Old table '{old_table_name}' not found. Assuming schema update for potentially existing '{new_table_name}'.")
            # 舊表不存在，直接嘗試更新新表結構 (如果新表存在的話)
            cursor.close() # 關閉當前游標
            return update_form_table_schema(new_form_identifier, form_json)

        # 2. 檢查新資料表是否已存在 (避免衝突)
        cursor.execute(f"""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ? AND TABLE_CATALOG = ?
        """, (new_table_name, DB_NAME))
        if cursor.fetchone():
            abort(409, description=f"Target table name '{new_table_name}' already exists. Cannot rename.")

        # --- 執行重新命名 ---
        # 3. 重新命名資料表
        rename_sql = f"EXEC sp_rename '[dbo].[{old_table_name}]', '{new_table_name}'"
        current_app.logger.info(f"Executing rename: {rename_sql}")
        cursor.execute(rename_sql)
        
        # 4. 重新命名主鍵約束
        old_pk_name = f"PK_{old_table_name}"
        new_pk_name = f"PK_{new_table_name}"
        try:
            rename_pk_sql = f"EXEC sp_rename N'[dbo].[{old_pk_name}]', N'{new_pk_name}', N'OBJECT'"
            current_app.logger.info(f"Executing PK rename: {rename_pk_sql}")
            cursor.execute(rename_pk_sql)
        except Exception as pk_e:
            current_app.logger.warning(f"Could not rename primary key '{old_pk_name}' to '{new_pk_name}'. It might not exist or have a different name. Error: {pk_e}")

        # 5. 重新命名標識符列
        old_id_col = f"{old_table_name}Id"
        new_id_col = f"{new_table_name}Id"
        try:
            # 檢查舊 ID 列是否存在於新表中
            cursor.execute(f"""
                SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ? AND COLUMN_NAME = ? AND TABLE_CATALOG = ?
            """, (new_table_name, old_id_col, DB_NAME))
            if cursor.fetchone():
                 rename_col_sql = f"EXEC sp_rename N'[dbo].[{new_table_name}].[{old_id_col}]', N'{new_id_col}', 'COLUMN'"
                 current_app.logger.info(f"Executing column rename: {rename_col_sql}")
                 cursor.execute(rename_col_sql)
            else:
                 current_app.logger.warning(f"Old ID column '{old_id_col}' not found in the renamed table '{new_table_name}'. Skipping column rename.")
        except Exception as col_e:
            current_app.logger.warning(f"Could not rename column '{old_id_col}' to '{new_id_col}'. Error: {col_e}")
        
        rename_success = True
        current_app.logger.info(f"Successfully renamed table components from '{old_table_name}' to '{new_table_name}'.")

    except Exception as e:
        current_app.logger.error(f"Error during table rename process from '{old_table_name}' to '{new_table_name}': {str(e)}")
        # sp_rename 錯誤通常無法回滾，這裡只能記錄錯誤並中止
        abort(500, description=f"Error renaming table: {str(e)}")
    finally:
         if cursor:
              cursor.close() # 關閉用於重命名的游標

    # --- 如果重命名成功，接著更新結構 ---
    if rename_success:
        try:
            update_result = update_form_table_schema(new_form_identifier, form_json)
            return {
                "success": True,
                "message": f"Table renamed to {new_table_name} and schema updated successfully.",
                "table_name": new_table_name,
                "schema_update_details": update_result
            }
        except Exception as update_e:
             # 如果更新結構失敗，表已經被重命名了
             current_app.logger.error(f"Table was renamed to '{new_table_name}', but schema update failed: {str(update_e)}")
             # 返回部分成功的訊息或錯誤
             abort(500, description=f"Table renamed, but schema update failed: {str(update_e)}")
    else:
         # 理論上如果重命名失敗，上面已經 abort 了
         abort(500, description="Table rename failed.")


def update_form_table_schema(form_identifier, form_json, existing_cursor=None, db_name_param=None):
    """
    輔助函數：更新指定 user_ 資料表的結構以匹配 formJson (僅新增欄位)。
    可以接收現有的資料庫游標以在事務中執行 (但目前未使用)。
    如果表不存在，則報錯。
    """
    # 確保 formJson 是字典
    if isinstance(form_json, str):
        try:
            form_json = json.loads(form_json)
        except json.JSONDecodeError:
            abort(400, description="Invalid JSON in formJson for schema update")
    if not isinstance(form_json, dict):
         abort(400, description="formJson must be a valid JSON object for schema update.")

    db = get_db()
    # 如果傳入了游標，則使用它，否則創建新的
    cursor = existing_cursor or db.cursor() 
    
    db_name = db_name_param or DB_NAME
    table_name = f"user_{form_identifier}"

    current_app.logger.info(f"Updating schema for table '{table_name}' in database '{db_name}'")

    try:
        # 1. 檢查資料表是否存在
        cursor.execute(f"""
            SELECT 1 FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ? AND TABLE_CATALOG = ?
        """, (table_name, db_name))
        if not cursor.fetchone():
             current_app.logger.error(f"Table '{table_name}' not found for schema update.")
             abort(404, description=f"Table '{table_name}' not found. Cannot update schema.")

        # 2. 解析 formJson 獲取所有 ItemId
        required_item_ids = []
        collect_items(form_json.get('Elements', []), required_item_ids)
        
        if not required_item_ids:
            current_app.logger.warning(f"No items found in formJson for table '{table_name}'. No schema changes needed.")
            return {"message": "No items found in JSON, no schema changes applied.", "added_columns": []}

        # 3. 獲取資料表現有的 Item 欄位 (不含 _Remark)
        cursor.execute(f"""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ? 
            AND COLUMN_NAME LIKE 'Item[0-9]%' AND COLUMN_NAME NOT LIKE '%_Remark'
            AND TABLE_CATALOG = ?
        """, (table_name, db_name))
        existing_item_columns = {row[0] for row in cursor.fetchall()}
        
        # 4. 計算需要新增的欄位 (ItemX 和 ItemX_Remark)
        columns_to_add_sql = []
        added_column_names_log = []
        for item_id in required_item_ids:
            col_name = f"Item{item_id}"
            remark_col_name = f"Item{item_id}_Remark"
            # 檢查 ItemX 是否已存在
            if col_name not in existing_item_columns:
                columns_to_add_sql.append(f"[{col_name}] [nvarchar](max) NULL")
                columns_to_add_sql.append(f"[{remark_col_name}] [nvarchar](max) NULL")
                added_column_names_log.append(col_name)
                added_column_names_log.append(remark_col_name)

        # 5. 如果有需要新增的欄位，執行 ALTER TABLE
        if columns_to_add_sql:
            alter_sql = f"ALTER TABLE [dbo].[{table_name}] ADD {', '.join(columns_to_add_sql)}"
            current_app.logger.info(f"Executing schema update for {table_name}: Adding columns {added_column_names_log}")
            cursor.execute(alter_sql)
            
            # 只有當未使用外部游標時才提交
            if not existing_cursor:
                db.commit()
            current_app.logger.info(f"Successfully added columns to {table_name}: {added_column_names_log}")
        else:
            current_app.logger.info(f"No new columns needed for table '{table_name}'. Schema is up-to-date.")

        return {
             "message": f"Schema update for {table_name} completed.",
             "added_columns": added_column_names_log # 返回實際新增的欄位名列表
        }

    except Exception as e:
        # 只有當未使用外部游標時才回滾
        if not existing_cursor: 
            db.rollback()
        current_app.logger.error(f"Error updating schema for table {table_name}: {str(e)}")
        # 如果在事務中 (雖然這裡沒用)，向上拋出異常
        if existing_cursor:
             raise e 
        else:
             abort(500, description=f"Error updating table schema: {str(e)}")
    finally:
        # 只有當未使用外部游標時才關閉游標
        if not existing_cursor and cursor:
            cursor.close()

