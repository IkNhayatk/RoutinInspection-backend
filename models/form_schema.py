import json
# import logging # logging 已被 current_app.logger 取代
from flask import abort, current_app # 新增 current_app
from db import get_db

# TODO: 將資料庫名稱設為可配置 (例如，從環境變數或設定檔讀取) -> 這個 TODO 現在可以解決了
# 移除這一行 -> DB_NAME = 'RoutinInspection_dev' # 或 'RoutinInspection'

def collect_items(element, items_list):
    """
    遞迴函數，收集 JSON 結構中所有有效的 ItemId。
    確保 ItemId 是整數且不重複。
    """
    if isinstance(element, dict):
        # 檢查是否為 Item 類型且包含 ItemId
        if element.get('ElmentType') == 'Item' and 'ItemId' in element:
            try:
                item_id = int(element['ItemId'])
                # 只有當 ItemId 是有效整數且尚未加入列表時才添加
                if item_id not in items_list:
                    items_list.append(item_id)
            except (ValueError, TypeError):
                 # 記錄無效的 ItemId 但繼續處理
                 current_app.logger.warning(f"Skipping invalid or non-integer ItemId: {element.get('ItemId')}")
        
        # 遞迴處理 'Elements' (如果是列表或字典)
        if 'Elements' in element:
            elements_value = element['Elements']
            if isinstance(elements_value, list):
                for sub_element in elements_value:
                    collect_items(sub_element, items_list)
            elif isinstance(elements_value, dict): # 處理 Elements 是單個物件的情況
                 collect_items(elements_value, items_list)
        
        # (可選) 如果需要遞迴處理字典中的其他值 (可能是巢狀結構)
        # for key, value in element.items():
        #     if key != 'Elements' and isinstance(value, (dict, list)):
        #          collect_items(value, items_list)

    # 如果元素本身是列表，遞迴處理列表中的每個元素
    elif isinstance(element, list):
        for sub_element in element:
            collect_items(sub_element, items_list)

    # 其他類型 (如字串、數字) 不包含 ItemId，直接忽略

def get_configured_db_name():
    """輔助函數：從配置中獲取資料庫名稱"""
    db_name = current_app.config.get('DB_NAME')
    if not db_name:
        current_app.logger.error("CRITICAL: DB_NAME is not configured in the application.")
        # 根據您的應用需求，如果 DB_NAME 未設定，可能需要拋出異常
        raise ValueError("DB_NAME is not configured.")
    return db_name

def create_form_table(form_data):
    """
    根據表單 JSON 建立新的 user_ 資料表。
    如果已存在同名資料表，會先刪除再重建。
    form_data 需包含:
    - formIdentifier: 表單識別符 (用作資料表名稱)
    - formJson: 表單 JSON 結構 (可以是字串或已解析的 dict)
    """
    db = get_db() # 這裡的 db 連接已經是針對 config 中的 DB_NAME 建立的
    cursor = db.cursor()
    
    # 從配置獲取資料庫名稱，主要用於日誌或特定的 SQL 查詢 (如 INFORMATION_SCHEMA)
    # 對於常規的 CREATE TABLE, DROP TABLE，因為已連接到目標資料庫，所以不需要顯式指定 DB_NAME
    # 但在某些 SQL (如 sp_rename 的某些用法或跨資料庫查詢) 中可能需要
    # 在這個檔案的目前用法中，主要是用在日誌和 INFORMATION_SCHEMA 查詢
    try:
        db_name_for_logging = get_configured_db_name()
    except ValueError:
        # 如果 DB_NAME 未設定，這裡需要決定如何處理，create_form_table 可能無法安全執行
        abort(500, description="Database name not configured, cannot proceed with table creation.")


    form_identifier = form_data.get('formIdentifier')
    if not form_identifier:
        abort(400, description="Missing formIdentifier for table creation.")
    
    trimmed_identifier = form_identifier.strip()
    table_name = trimmed_identifier if trimmed_identifier.startswith("user_") else f"user_{trimmed_identifier}"
    
    form_json = form_data.get('formJson')
    if isinstance(form_json, str):
        try:
            form_json = json.loads(form_json)
        except json.JSONDecodeError:
            abort(400, description="Invalid JSON in formJson for table creation.")
    
    if not isinstance(form_json, dict):
        abort(400, description="formJson must be a valid JSON object.")
    
    current_app.logger.info(f"Attempting to create table '{table_name}' in database '{db_name_for_logging}'")

    try:
        item_ids = []
        collect_items(form_json.get('Elements', []), item_ids)
        
        if not item_ids:
            current_app.logger.warning(f"No items found in formJson for '{form_identifier}'. Creating table with base columns only.")

        # 注意：這裡的 SQL Server 特定語法 IF OBJECT_ID...
        # 它在當前連接的資料庫上下文中操作，所以不需要指定 DB_NAME
        cursor.execute(f"IF OBJECT_ID(N'[dbo].[{table_name}]', N'U') IS NOT NULL DROP TABLE [dbo].[{table_name}]")
        current_app.logger.info(f"Dropped existing table '{table_name}' if it existed in current database.")
        
        base_columns = [
            f"[{table_name}Id] [int] IDENTITY(1,1) NOT NULL",
            "[UserId] [int] NULL",
            "[PointInfoId] [int] NULL",
            "[TableName] [nchar](32) NULL",
            "[ReviewerId] [int] NULL",
            "[ReviewerComment] [nchar](32) NULL",
            "[CheckDate] [datetime] NULL"
        ]
        
        item_columns = [f"[Item{item_id}] [nvarchar](max) NULL, [Item{item_id}_Remark] [nvarchar](max) NULL" for item_id in item_ids]
            
        all_columns_str = ",\n            ".join(base_columns + item_columns)

        primary_key_constraint = f"""
         CONSTRAINT [PK_{table_name}] PRIMARY KEY CLUSTERED 
        (
            [{table_name}Id] ASC
        )WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
        """

        create_table_sql = f"""
        CREATE TABLE [dbo].[{table_name}](
            {all_columns_str}
            ,{primary_key_constraint} 
        ) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
        """
        # 注意：主鍵約束前面加了逗號，因為它是 CREATE TABLE 列表中的最後一個元素
        
        current_app.logger.debug(f"Executing CREATE TABLE SQL for {table_name}:\n{create_table_sql}")
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
    if not old_form_identifier or not new_form_identifier:
        abort(400, description="Old and new form identifiers are required for rename/update.")
    
    # 從配置獲取 DB_NAME，主要用於 INFORMATION_SCHEMA 查詢
    try:
        db_name_for_schema_checks = get_configured_db_name()
    except ValueError:
        abort(500, description="Database name not configured, cannot proceed with table rename/update.")

    if old_form_identifier == new_form_identifier:
        current_app.logger.info(f"Form identifier '{new_form_identifier}' unchanged, only updating schema.")
        # 傳遞 db_name_for_schema_checks 給 update_form_table_schema
        return update_form_table_schema(new_form_identifier, form_json, db_name_param=db_name_for_schema_checks)

    db = get_db()
    old_table_name = f"user_{old_form_identifier}"
    new_table_name = f"user_{new_form_identifier}"
    
    current_app.logger.info(f"Attempting to rename table '{old_table_name}' to '{new_table_name}' in database '{db_name_for_schema_checks}'")

    rename_success = False
    cursor = db.cursor()
    try:
        # 檢查舊表時，TABLE_CATALOG 使用配置的 DB_NAME
        cursor.execute(f"""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ? AND TABLE_CATALOG = ? 
        """, (old_table_name, db_name_for_schema_checks))
        if not cursor.fetchone():
            current_app.logger.warning(f"Old table '{old_table_name}' not found. Assuming schema update for potentially existing '{new_table_name}'.")
            cursor.close()
            return update_form_table_schema(new_form_identifier, form_json, db_name_param=db_name_for_schema_checks)

        # 檢查新表時，TABLE_CATALOG 使用配置的 DB_NAME
        cursor.execute(f"""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ? AND TABLE_CATALOG = ?
        """, (new_table_name, db_name_for_schema_checks))
        if cursor.fetchone():
            abort(409, description=f"Target table name '{new_table_name}' already exists. Cannot rename.")

        # sp_rename 在當前資料庫執行，通常不需要顯式指定 DB_NAME
        rename_sql = f"EXEC sp_rename '[dbo].[{old_table_name}]', '{new_table_name}'"
        cursor.execute(rename_sql)
        
        old_pk_name = f"PK_{old_table_name}"
        new_pk_name = f"PK_{new_table_name}"
        try:
            rename_pk_sql = f"EXEC sp_rename N'[dbo].[{old_pk_name}]', N'{new_pk_name}', N'OBJECT'"
            cursor.execute(rename_pk_sql)
        except Exception as pk_e:
            current_app.logger.warning(f"Could not rename primary key '{old_pk_name}' to '{new_pk_name}'. Error: {pk_e}")

        old_id_col = f"{old_table_name}Id"
        new_id_col = f"{new_table_name}Id"
        try:
            # 檢查舊 ID 列時，TABLE_CATALOG 使用配置的 DB_NAME
            cursor.execute(f"""
                SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ? AND COLUMN_NAME = ? AND TABLE_CATALOG = ?
            """, (new_table_name, old_id_col, db_name_for_schema_checks))
            if cursor.fetchone():
                 rename_col_sql = f"EXEC sp_rename N'[dbo].[{new_table_name}].[{old_id_col}]', N'{new_id_col}', 'COLUMN'"
                 cursor.execute(rename_col_sql)
            else:
                 current_app.logger.warning(f"Old ID column '{old_id_col}' not found in renamed table '{new_table_name}'. Skipping.")
        except Exception as col_e:
            current_app.logger.warning(f"Could not rename column '{old_id_col}' to '{new_id_col}'. Error: {col_e}")
        
        rename_success = True
        current_app.logger.info(f"Successfully renamed table components from '{old_table_name}' to '{new_table_name}'.")

    except Exception as e:
        current_app.logger.error(f"Error during table rename from '{old_table_name}' to '{new_table_name}': {str(e)}")
        abort(500, description=f"Error renaming table: {str(e)}")
    finally:
         if cursor:
              cursor.close()

    if rename_success:
        try:
            # 傳遞 db_name_for_schema_checks 給 update_form_table_schema
            update_result = update_form_table_schema(new_form_identifier, form_json, db_name_param=db_name_for_schema_checks)
            return {
                "success": True,
                "message": f"Table renamed to {new_table_name} and schema updated successfully.",
                "table_name": new_table_name,
                "schema_update_details": update_result
            }
        except Exception as update_e:
             current_app.logger.error(f"Table renamed to '{new_table_name}', but schema update failed: {str(update_e)}")
             abort(500, description=f"Table renamed, but schema update failed: {str(update_e)}")
    else:
         abort(500, description="Table rename failed.")


def update_form_table_schema(form_identifier, form_json, existing_cursor=None, db_name_param=None):
    """
    輔助函數：更新指定 user_ 資料表的結構以匹配 formJson (僅新增欄位)。
    db_name_param 應該是從配置中獲取的資料庫名稱，用於 INFORMATION_SCHEMA 查詢。
    """
    if isinstance(form_json, str):
        try:
            form_json = json.loads(form_json)
        except json.JSONDecodeError:
            abort(400, description="Invalid JSON in formJson for schema update")
    if not isinstance(form_json, dict):
         abort(400, description="formJson must be a valid JSON object for schema update.")

    db = get_db() # 當前連接的資料庫
    cursor = existing_cursor or db.cursor() 
    
    # 使用傳入的 db_name_param (來自 get_configured_db_name())
    # 如果未傳入，則嘗試重新獲取 (雖然理想情況下應該總是傳入)
    db_name_for_checks = db_name_param or get_configured_db_name()
    if not db_name_for_checks: # 再次檢查，以防萬一
        abort(500, description="Database name not configured for schema update.")

    table_name = f"user_{form_identifier}"
    current_app.logger.info(f"Updating schema for table '{table_name}' in database '{db_name_for_checks}'")

    try:
        # 查詢 INFORMATION_SCHEMA.TABLES 時，TABLE_CATALOG 使用配置的 DB_NAME
        cursor.execute(f"""
            SELECT 1 FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ? AND TABLE_CATALOG = ?
        """, (table_name, db_name_for_checks))
        if not cursor.fetchone():
             current_app.logger.error(f"Table '{table_name}' not found for schema update in db '{db_name_for_checks}'.")
             abort(404, description=f"Table '{table_name}' not found. Cannot update schema.")

        required_item_ids = []
        collect_items(form_json.get('Elements', []), required_item_ids)
        
        if not required_item_ids:
            current_app.logger.info(f"No items in formJson for '{table_name}'. No schema changes.")
            return {"message": "No items in JSON, no schema changes.", "added_columns": []}

        # 查詢 INFORMATION_SCHEMA.COLUMNS 時，TABLE_CATALOG 使用配置的 DB_NAME
        cursor.execute(f"""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ? 
            AND COLUMN_NAME LIKE 'Item[0-9]%' AND COLUMN_NAME NOT LIKE '%_Remark'
            AND TABLE_CATALOG = ?
        """, (table_name, db_name_for_checks))
        existing_item_columns = {row[0] for row in cursor.fetchall()}
        
        columns_to_add_sql = []
        added_column_names_log = []
        for item_id in required_item_ids:
            col_name = f"Item{item_id}"
            remark_col_name = f"Item{item_id}_Remark"
            if col_name not in existing_item_columns:
                columns_to_add_sql.append(f"[{col_name}] [nvarchar](max) NULL")
                columns_to_add_sql.append(f"[{remark_col_name}] [nvarchar](max) NULL")
                added_column_names_log.extend([col_name, remark_col_name])

        if columns_to_add_sql:
            # ALTER TABLE 在當前資料庫執行
            alter_sql = f"ALTER TABLE [dbo].[{table_name}] ADD {', '.join(columns_to_add_sql)}"
            current_app.logger.info(f"Executing schema update for {table_name}: Adding {added_column_names_log}")
            cursor.execute(alter_sql)
            if not existing_cursor: db.commit()
            current_app.logger.info(f"Successfully added columns to {table_name}: {added_column_names_log}")
        else:
            current_app.logger.info(f"No new columns needed for table '{table_name}'.")

        return {"message": f"Schema update for {table_name} completed.", "added_columns": added_column_names_log}
    except Exception as e:
        if not existing_cursor: db.rollback()
        current_app.logger.error(f"Error updating schema for table {table_name}: {str(e)}")
        if existing_cursor: raise e 
        else: abort(500, description=f"Error updating table schema: {str(e)}")
    finally:
        if not existing_cursor and cursor: cursor.close()