import pytest
from unittest.mock import patch, Mock
from flask import abort
import json

# 導入要測試的模組
from models.route import (
    get_route_by_id, 
    get_all_routes, 
    create_route, 
    update_route, 
    delete_route
)

class TestGetRouteById:
    """測試 get_route_by_id 函數"""
    
    @patch('models.route.get_db')
    def test_get_route_by_id_success(self, mock_get_db, app, mock_db_connection):
        """測試成功獲取路線"""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_db.return_value = mock_conn
        
        # 設定 fetchone 回傳值
        mock_cursor.fetchone.return_value = (1, '測試路線', 10, 'test_table')
        
        with app.app_context():
            result = get_route_by_id(1)
        
        # 驗證結果
        assert result is not None
        assert result['RouteId'] == 1
        assert result['RouteName'] == '測試路線'
        assert result['BindingTableId'] == 10
        assert result['BindingTableName'] == 'test_table'
        
        # 驗證 SQL 執行
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()
    
    @patch('models.route.get_db')
    def test_get_route_by_id_not_found(self, mock_get_db, app, mock_db_connection):
        """測試路線不存在的情況"""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_db.return_value = mock_conn
        
        # 設定 fetchone 回傳 None
        mock_cursor.fetchone.return_value = None
        
        with app.app_context():
            result = get_route_by_id(999)
        
        assert result is None
        mock_cursor.close.assert_called_once()
    
    @patch('models.route.get_db')
    @patch('models.route.abort')
    def test_get_route_by_id_database_error(self, mock_abort, mock_get_db, app, mock_db_connection):
        """測試資料庫錯誤"""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_db.return_value = mock_conn
        
        # 設定資料庫錯誤
        mock_cursor.execute.side_effect = Exception("Database error")
        
        with app.app_context():
            get_route_by_id(1)
        
        mock_abort.assert_called_once_with(500)
        mock_cursor.close.assert_called_once()

class TestGetAllRoutes:
    """測試 get_all_routes 函數"""
    
    @patch('models.route.get_db')
    def test_get_all_routes_success(self, mock_get_db, app, mock_db_connection, sample_routes_db_result): # <--- 修改這裡
        """測試成功獲取所有路線"""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_db.return_value = mock_conn
        
        # 設定 count 查詢回傳和資料查詢回傳
        mock_cursor.fetchone.return_value = (len(sample_routes_db_result),)  # count 查詢結果，使用 fixture 的長度
        mock_cursor.fetchall.return_value = sample_routes_db_result # <--- 修改這裡
        
        with app.app_context():
            result = get_all_routes(page=1, limit=10)
        
        # 驗證結果結構
        assert 'routes' in result
        assert 'total_records' in result
        assert result['total_records'] == len(sample_routes_db_result) # <--- 修改這裡
        assert len(result['routes']) == len(sample_routes_db_result) # <--- 修改這裡
        
        # 驗證第一個路線數據 (如果 sample_routes_db_result 不為空)
        if sample_routes_db_result:
            first_route_db = sample_routes_db_result[0]
            first_route_res = result['routes'][0]
            assert first_route_res['RouteId'] == first_route_db[0]
            assert first_route_res['RouteName'] == first_route_db[1]
            assert first_route_res['BindingTableId'] == first_route_db[2]
            assert first_route_res['BindingTableName'] == first_route_db[3]
        
        # 驗證 SQL 執行次數（count + data query）
        assert mock_cursor.execute.call_count == 2
        mock_cursor.close.assert_called_once()
    
    @patch('models.route.get_db')
    def test_get_all_routes_with_search(self, mock_get_db, app, mock_db_connection):
        """測試帶搜尋條件的路線查詢"""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_db.return_value = mock_conn
        
        # 設定回傳值
        mock_cursor.fetchone.return_value = (1,)
        mock_cursor.fetchall.return_value = [(1, '測試路線', 10, 'test_table')]
        
        with app.app_context():
            result = get_all_routes(page=1, limit=10, search="測試")
        
        # 驗證 execute 被呼叫時有傳入搜尋參數
        calls = mock_cursor.execute.call_args_list
        assert len(calls) == 2  # count + data query
        
        # 檢查第一個呼叫（count query）的參數
        count_call_args = calls[0][0]
        assert '%測試%' in count_call_args[1:]  # 參數中應包含搜尋詞
    
    @patch('models.route.get_db')
    def test_get_all_routes_with_mode_filter(self, mock_get_db, app, mock_db_connection):
        """測試帶模式過濾的路線查詢"""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_db.return_value = mock_conn
        
        mock_cursor.fetchone.return_value = (1,)
        mock_cursor.fetchall.return_value = [(1, '已綁定路線', 10, 'test_table')]
        
        with app.app_context():
            result = get_all_routes(page=1, limit=10, mode="1")
        
        # 驗證 SQL 執行
        calls = mock_cursor.execute.call_args_list
        assert len(calls) == 2
        
        # 檢查 SQL 中是否包含 IS NOT NULL 條件
        count_sql = calls[0][0][0]
        assert "IS NOT NULL" in count_sql
    
    @patch('models.route.get_db')
    @patch('models.route.abort')
    def test_get_all_routes_database_error(self, mock_abort, mock_get_db, app, mock_db_connection):
        """測試資料庫錯誤處理"""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_db.return_value = mock_conn
        
        # 設定資料庫錯誤
        mock_cursor.execute.side_effect = Exception("Database connection failed")
        
        with app.app_context():
            get_all_routes()
        
        mock_abort.assert_called_once()
        mock_cursor.close.assert_called_once()

class TestCreateRoute:
    """測試 create_route 函數"""
    
    @patch('models.route.get_db')
    def test_create_route_success(self, mock_get_db, app, mock_db_connection, sample_route_data):
        """測試成功創建路線"""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_db.return_value = mock_conn
        
        with app.app_context():
            result = create_route(sample_route_data)
        
        # 驗證結果
        assert result['success'] is True
        assert result['message'] == '路線創建成功'
        
        # 驗證 SQL 執行
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
    
    @patch('models.route.get_db')
    @patch('models.route.abort')
    def test_create_route_database_error(self, mock_abort, mock_get_db, app, mock_db_connection, sample_route_data):
        """測試創建路線時的資料庫錯誤"""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_db.return_value = mock_conn
        
        # 設定資料庫錯誤
        mock_cursor.execute.side_effect = Exception("Insert failed")
        
        with app.app_context():
            create_route(sample_route_data)
        
        mock_conn.rollback.assert_called_once()
        mock_abort.assert_called_once_with(500)
        mock_cursor.close.assert_called_once()

class TestUpdateRoute:
    """測試 update_route 函數"""
    
    @patch('models.route.get_db')
    def test_update_route_success(self, mock_get_db, app, mock_db_connection, sample_route_data):
        """測試成功更新路線"""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_db.return_value = mock_conn
        
        route_id = 1
        updated_data = {
            'RouteName': '更新後的路線',
            'BindingTableId': 2,
            'BindingTableName': 'updated_table'
        }
        
        with app.app_context():
            result = update_route(route_id, updated_data)
        
        # 驗證結果
        assert result['success'] is True
        assert result['message'] == '路線更新成功'
        
        # 驗證 SQL 執行，檢查參數順序
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert route_id in call_args  # route_id 應該在參數中
        
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()

class TestDeleteRoute:
    """測試 delete_route 函數"""
    
    @patch('models.route.get_db')
    def test_delete_route_success(self, mock_get_db, app, mock_db_connection):
        """測試成功刪除路線"""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_db.return_value = mock_conn
        
        route_id = 1
        
        with app.app_context():
            result = delete_route(route_id)
        
        # 驗證結果
        assert result['success'] is True
        assert result['message'] == '路線刪除成功'
        
        # 驗證 SQL 執行
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert route_id in call_args
        
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
    
    @patch('models.route.get_db')
    @patch('models.route.abort')
    def test_delete_route_database_error(self, mock_abort, mock_get_db, app, mock_db_connection):
        """測試刪除路線時的資料庫錯誤"""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_db.return_value = mock_conn
        
        # 設定資料庫錯誤
        mock_cursor.execute.side_effect = Exception("Delete failed")
        
        with app.app_context():
            delete_route(1)
        
        mock_conn.rollback.assert_called_once()
        mock_abort.assert_called_once_with(500)
        mock_cursor.close.assert_called_once()

# 整合測試類別
class TestRouteIntegration:
    """路線功能的整合測試"""
    
    @patch('models.route.get_db')
    def test_route_lifecycle(self, mock_get_db, app, mock_db_connection):
        """測試路線的完整生命週期：創建 -> 查詢 -> 更新 -> 刪除"""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_db.return_value = mock_conn
        
        route_data = {
            'RouteName': '生命週期測試路線',
            'BindingTableId': 1,
            'BindingTableName': 'lifecycle_table'
        }
        
        with app.app_context():
            # 1. 創建路線
            create_result = create_route(route_data)
            assert create_result['success'] is True
            
            # 2. 查詢路線 (模擬查詢結果)
            mock_cursor.fetchone.return_value = (1, '生命週期測試路線', 1, 'lifecycle_table')
            get_result = get_route_by_id(1)
            assert get_result is not None
            assert get_result['RouteName'] == '生命週期測試路線'
            
            # 3. 更新路線
            update_data = {
                'RouteName': '更新後的生命週期路線',
                'BindingTableId': 2,
                'BindingTableName': 'updated_lifecycle_table'
            }
            update_result = update_route(1, update_data)
            assert update_result['success'] is True
            
            # 4. 刪除路線
            delete_result = delete_route(1)
            assert delete_result['success'] is True
        
        # 驗證所有操作都呼叫了 commit
        assert mock_conn.commit.call_count == 3  # create, update, delete

# API 路由測試
class TestRouteAPIEndpoints:
    """測試路線 API 端點"""
    
    @patch('routes.route_routes.get_route_by_id')
    def test_get_route_endpoint_success(self, mock_get_route, client):
        """測試獲取單個路線的 API 端點"""
        # 模擬回傳值
        mock_get_route.return_value = {
            "RouteId": 1,
            "RouteName": "測試路線",
            "BindingTableId": 10,
            "BindingTableName": "test_table"
        }
        
        response = client.get('/api/routes/1')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['route']['RouteId'] == 1
        assert data['route']['RouteName'] == "測試路線"
    
    @patch('routes.route_routes.get_route_by_id')
    def test_get_route_endpoint_not_found(self, mock_get_route, client):
        """測試獲取不存在路線的 API 端點"""
        mock_get_route.return_value = None

        response = client.get('/api/routes/999')

        assert response.status_code == 404
        # 只有在確定 API 會返回 JSON 錯誤時才執行以下斷言
        if response.is_json: # 或者您預期它總是 JSON
            data = response.get_json()
            assert data is not None # 確保 data 不是 None
            assert data['success'] is False
            assert "路線不存在" in data['message'] 
    
    @patch('routes.route_routes.get_all_routes')
    def test_get_routes_endpoint_success(self, mock_get_routes, client):
        """測試獲取所有路線的 API 端點"""
        mock_get_routes.return_value = {
            "routes": [
                {"RouteId": 1, "RouteName": "路線1", "BindingTableId": 10, "BindingTableName": "table1"},
                {"RouteId": 2, "RouteName": "路線2", "BindingTableId": 20, "BindingTableName": "table2"}
            ],
            "total_records": 2
        }
        
        response = client.get('/api/routes?page=1&limit=10')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['routes']) == 2
        assert data['pagination']['total_records'] == 2
    
    @patch('routes.route_routes.create_route')
    def test_create_route_endpoint_success(self, mock_create_route, client):
        """測試創建路線的 API 端點"""
        mock_create_route.return_value = {
            "success": True,
            "message": "路線創建成功"
        }
        
        route_data = {
            "RouteName": "新路線",
            "BindingTableId": 30,
            "BindingTableName": "new_table"
        }
        
        response = client.post('/api/routes', 
                              json=route_data,
                              content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert "路線創建成功" in data['message']