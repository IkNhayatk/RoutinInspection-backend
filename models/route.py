import json
from flask import abort, current_app
from db import get_db


""" SELECT TOP (1000) [RouteId]
      ,[RouteName]
      ,[BindingTableId]
      ,[BindingTableName]
  FROM [RoutinInspection_dev].[dbo].[Routes] """


def get_route_by_id(form_id):
    """獲取特定巡檢路線"""
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT TOP (1000) [RouteId], [RouteName], [BindingTableId], [BindingTableName] FROM [RoutinInspection_dev].[dbo].[Routes] WHERE RouteId = ?", form_id)
        row = cursor.fetchone()
        if row:
            return {
                "RouteId": row[0],
                "RouteName": row[1],
                "BindingTableId": row[2],
                "BindingTableName": row[3]
            }
        else:
            return None
    except Exception as e:
        current_app.logger.error(f"Error fetching route by ID: {e}")
        abort(500)
    finally:
        cursor.close()

def get_all_routes(page=1, limit=10, search=None, mode=None):
    """獲取所有巡檢路線，支援分頁、搜尋和模式過濾"""
    db = get_db()
    cursor = db.cursor()

    # SQL 查詢的基本組成部分
    select_fields = "[RouteId], [RouteName], [BindingTableId], [BindingTableName]"
    from_table = "[RoutinInspection_dev].[dbo].[Routes]"
    
    # 用於過濾的參數和 WHERE 子句
    filter_params = []
    where_clauses = []

    if search:
        # 假設搜尋適用於 RouteName 和 BindingTableName
        where_clauses.append("([RouteName] LIKE ? OR [BindingTableName] LIKE ?)")
        search_like_term = f"%{search}%"
        filter_params.extend([search_like_term, search_like_term])

    if mode:
        # 範例：如果 mode '1' 表示「已綁定」(BindingTableId 不是 null)
        # 根據 'mode' 的實際意義調整此邏輯。
        # 從日誌中看到 mode=1，這裡假設它用於過濾已綁定的路線。
        if mode == '1':
            where_clauses.append("[BindingTableId] IS NOT NULL")
        elif mode == '0': # 假設 mode '0' 表示「未綁定」
            where_clauses.append("[BindingTableId] IS NULL")
        # 如果 mode 可以是特定的 ID:
        # else:
        #     try:
        #         mode_id = int(mode)
        #         where_clauses.append("[BindingTableId] = ?")
        #         filter_params.append(mode_id)
        #     except ValueError:
        #         current_app.logger.warning(f"用於 ID 過濾的 mode 值 '{mode}' 無效。")
        else:
            current_app.logger.warning(f"未處理的 mode 參數值: '{mode}'。將忽略 mode 過濾。")


    where_string = ""
    if where_clauses:
        where_string = " WHERE " + " AND ".join(where_clauses)

    total_records = 0
    routes = []

    try:
        # 首先，獲取符合過濾條件的總記錄數
        count_sql = f"SELECT COUNT(*) FROM {from_table}{where_string}"
        current_app.logger.debug(f"執行計數查詢: {count_sql}，參數: {filter_params}")
        cursor.execute(count_sql, *filter_params) # 使用 * 解包參數列表
        result = cursor.fetchone()
        if result:
            total_records = result[0]
        
        # 然後，獲取分頁後的資料
        offset = (page - 1) * limit
        # SQL Server 的 OFFSET FETCH 需要 ORDER BY 子句
        # 使用 RouteId 進行排序，如果其他列更合適，請更改
        order_by_clause = "ORDER BY RouteId" 
        
        # SQL Server 2012+ 的正確分頁語法
        pagination_clause = "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        
        data_sql = f"SELECT {select_fields} FROM {from_table}{where_string} {order_by_clause} {pagination_clause}"
        
        # 資料查詢的參數是 filter_params 加上分頁參數
        data_params = filter_params + [offset, limit]
        
        current_app.logger.debug(f"執行資料查詢: {data_sql}，參數: {data_params}")
        cursor.execute(data_sql, *data_params) # 使用 * 解包參數列表
        
        rows = cursor.fetchall()
        for row in rows:
            routes.append({
                "RouteId": row[0],
                "RouteName": row[1],
                "BindingTableId": row[2], # 如果可為 null，則可能為 None
                "BindingTableName": row[3] # 如果可為 null，則可能為 None
            })
            
        return {
            "routes": routes,
            "total_records": total_records # 使用 COUNT(*) 查詢的總數
        }

    except Exception as e:
        current_app.logger.error(f"get_all_routes 中的資料庫錯誤: {e}", exc_info=True)
        # 重新引發或中止，以確保路由處理程序返回 500 錯誤
        # 原始程式碼使用 abort(500)
        abort(500, description=f"獲取路線時發生錯誤: {str(e)}")
    finally:
        cursor.close()

def create_route(data):
    """創建新的巡檢路線"""
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("INSERT INTO [RoutinInspection_dev].[dbo].[Routes] ([RouteName], [BindingTableId], [BindingTableName]) VALUES (?, ?, ?)",
                       data['RouteName'], data['BindingTableId'], data['BindingTableName'])
        db.commit()
        return {
            "success": True,
            "message": "路線創建成功"
        }
    except Exception as e:
        current_app.logger.error(f"Error creating route: {e}")
        db.rollback()
        abort(500)
    finally:
        cursor.close()

def update_route(route_id, data):
    """更新巡檢路線"""
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("UPDATE [RoutinInspection_dev].[dbo].[Routes] SET [RouteName] = ?, [BindingTableId] = ?, [BindingTableName] = ? WHERE RouteId = ?",
                       data['RouteName'], data['BindingTableId'], data['BindingTableName'], route_id)
        db.commit()
        return {
            "success": True,
            "message": "路線更新成功"
        }
    except Exception as e:
        current_app.logger.error(f"Error updating route: {e}")
        db.rollback()
        abort(500)
    finally:
        cursor.close()

def delete_route(route_id):
    """刪除巡檢路線"""
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM [RoutinInspection_dev].[dbo].[Routes] WHERE RouteId = ?", route_id)
        db.commit()
        return {
            "success": True,
            "message": "路線刪除成功"
        }
    except Exception as e:
        current_app.logger.error(f"Error deleting route: {e}")
        db.rollback()
        abort(500)
    finally:
        cursor.close()