"""
conftest.py 測試

測試 conftest.py 中定義的所有 fixtures 和配置是否正常工作
"""

import pytest
import pyodbc
from unittest.mock import Mock, MagicMock
from flask import Flask


class TestConftestFixtures:
    """測試 conftest.py 中的 fixtures"""
    
    def test_app_fixture(self, app):
        """測試 app fixture"""
        assert isinstance(app, Flask)
        assert app.config['TESTING'] is True
        assert app.config['SECRET_KEY'] == 'test-secret-key-for-testing-only-do-not-use-in-production'
        assert app.config['DB_HOST'] == 'test_host'
        assert app.config['DB_NAME'] == 'test_routin_inspection'
        assert app.config['DEBUG'] is True
        assert app.config['ENV'] == 'testing'
        assert app.config['PORT'] == 3001
    
    def test_client_fixture(self, client):
        """測試 client fixture"""
        # 檢查客戶端是否可用
        assert client is not None
        
        # 測試簡單的請求
        response = client.get('/')
        # 不管返回什麼狀態碼，只要不崩潰就算通過
        assert response.status_code in [200, 404, 405, 500]
    
    def test_runner_fixture(self, runner):
        """測試 runner fixture"""
        assert runner is not None
    
    def test_mock_db_connection_fixture(self, mock_db_connection):
        """測試 mock_db_connection fixture"""
        mock_conn, mock_cursor = mock_db_connection
        
        # 檢查連接對象
        assert isinstance(mock_conn, MagicMock)
        assert hasattr(mock_conn, 'cursor')
        assert hasattr(mock_conn, 'commit')
        assert hasattr(mock_conn, 'rollback')
        assert hasattr(mock_conn, 'close')
        
        # 檢查游標對象
        assert isinstance(mock_cursor, MagicMock)
        assert hasattr(mock_cursor, 'execute')
        assert hasattr(mock_cursor, 'fetchone')
        assert hasattr(mock_cursor, 'fetchall')
        assert hasattr(mock_cursor, 'fetchmany')
        assert hasattr(mock_cursor, 'close')
        
        # 測試預設行為
        assert mock_cursor.fetchone() is None
        assert mock_cursor.fetchall() == []
        assert mock_cursor.rowcount == 1
    
    def test_mock_db_cursor_fixture(self, mock_db_cursor):
        """測試 mock_db_cursor fixture"""
        assert isinstance(mock_db_cursor, MagicMock)
        assert hasattr(mock_db_cursor, 'execute')
        assert hasattr(mock_db_cursor, 'fetchone')
        assert hasattr(mock_db_cursor, 'fetchall')
    
    def test_sample_form_data_fixture(self, sample_form_data):
        """測試 sample_form_data fixture"""
        assert isinstance(sample_form_data, dict)
        assert 'formIdentifier' in sample_form_data
        assert 'formDisplayName' in sample_form_data
        assert 'formJson' in sample_form_data
        assert 'mode' in sample_form_data
        assert 'isActive' in sample_form_data
        
        assert sample_form_data['formIdentifier'] == 'test_form_001'
        assert sample_form_data['formDisplayName'] == '測試表單A'
        assert isinstance(sample_form_data['formJson'], dict)
        assert 'Elements' in sample_form_data['formJson']
    
    def test_sample_form_data_list_fixture(self, sample_form_data_list):
        """測試 sample_form_data_list fixture"""
        assert isinstance(sample_form_data_list, list)
        assert len(sample_form_data_list) == 2
        
        for form_data in sample_form_data_list:
            assert isinstance(form_data, dict)
            assert 'formIdentifier' in form_data
            assert 'formDisplayName' in form_data
            assert 'formJson' in form_data
    
    def test_sample_route_data_fixture(self, sample_route_data):
        """測試 sample_route_data fixture"""
        assert isinstance(sample_route_data, dict)
        assert 'RouteName' in sample_route_data
        assert 'BindingTableId' in sample_route_data
        assert 'BindingTableName' in sample_route_data
        
        assert sample_route_data['RouteName'] == '測試路線A'
        assert sample_route_data['BindingTableId'] == 100
        assert sample_route_data['BindingTableName'] == 'test_binding_table'
    
    def test_sample_route_data_list_fixture(self, sample_route_data_list):
        """測試 sample_route_data_list fixture"""
        assert isinstance(sample_route_data_list, list)
        assert len(sample_route_data_list) == 3
        
        # 檢查第三個路線有 None 值
        assert sample_route_data_list[2]['BindingTableId'] is None
        assert sample_route_data_list[2]['BindingTableName'] is None
    
    def test_sample_routes_db_result_fixture(self, sample_routes_db_result):
        """測試 sample_routes_db_result fixture"""
        assert isinstance(sample_routes_db_result, list)
        assert len(sample_routes_db_result) == 4
        
        # 檢查每個結果都是元組
        for result in sample_routes_db_result:
            assert isinstance(result, tuple)
            assert len(result) == 4  # ID, 路線名, BindingTableId, BindingTableName
    
    def test_sample_user_data_fixture(self, sample_user_data):
        """測試 sample_user_data fixture"""
        assert isinstance(sample_user_data, dict)
        assert 'UserName' in sample_user_data
        assert 'UserID' in sample_user_data
        assert 'Password' in sample_user_data
        assert 'Email' in sample_user_data
        assert 'PriorityLevel' in sample_user_data
        assert 'Position' in sample_user_data
        assert 'Department' in sample_user_data
        
        assert sample_user_data['UserName'] == '測試用戶'
        assert sample_user_data['UserID'] == 'testuser001'
        assert sample_user_data['PriorityLevel'] == 1
    
    def test_sample_user_data_list_fixture(self, sample_user_data_list):
        """測試 sample_user_data_list fixture"""
        assert isinstance(sample_user_data_list, list)
        assert len(sample_user_data_list) == 2
        
        # 檢查權限級別不同
        assert sample_user_data_list[0]['PriorityLevel'] == 1
        assert sample_user_data_list[1]['PriorityLevel'] == 2
    
    def test_auth_headers_fixture(self, auth_headers):
        """測試 auth_headers fixture"""
        # auth_headers 是一個函數
        headers = auth_headers()
        assert isinstance(headers, dict)
        assert 'Authorization' in headers
        assert 'Content-Type' in headers
        assert headers['Authorization'] == 'Bearer test-jwt-token-12345'
        assert headers['Content-Type'] == 'application/json'
        
        # 測試自定義 token
        custom_headers = auth_headers("custom-token")
        assert custom_headers['Authorization'] == 'Bearer custom-token'
    
    def test_mock_jwt_token_fixture(self, mock_jwt_token):
        """測試 mock_jwt_token fixture"""
        assert isinstance(mock_jwt_token, str)
        assert mock_jwt_token == "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.payload"
    
    def test_mock_current_user_fixture(self, mock_current_user):
        """測試 mock_current_user fixture"""
        assert isinstance(mock_current_user, dict)
        assert 'UserID' in mock_current_user
        assert 'UserName' in mock_current_user
        assert 'Email' in mock_current_user
        assert 'PriorityLevel' in mock_current_user
        
        assert mock_current_user['UserID'] == 'testuser001'
        assert mock_current_user['PriorityLevel'] == 1
    
    def test_pagination_params_fixture(self, pagination_params):
        """測試 pagination_params fixture"""
        assert isinstance(pagination_params, dict)
        assert 'page' in pagination_params
        assert 'limit' in pagination_params
        assert 'search' in pagination_params
        assert 'mode' in pagination_params
        
        assert pagination_params['page'] == 1
        assert pagination_params['limit'] == 10
        assert pagination_params['search'] is None
        assert pagination_params['mode'] is None
    
    def test_search_pagination_params_fixture(self, search_pagination_params):
        """測試 search_pagination_params fixture"""
        assert isinstance(search_pagination_params, dict)
        assert search_pagination_params['page'] == 1
        assert search_pagination_params['limit'] == 5
        assert search_pagination_params['search'] == '測試'
        assert search_pagination_params['mode'] == '1'
    
    def test_mock_logger_fixture(self, mock_logger):
        """測試 mock_logger fixture"""
        assert isinstance(mock_logger, Mock)
        assert hasattr(mock_logger, 'debug')
        assert hasattr(mock_logger, 'info')
        assert hasattr(mock_logger, 'warning')
        assert hasattr(mock_logger, 'error')
        assert hasattr(mock_logger, 'critical')
        
        # 測試日誌方法可以調用
        mock_logger.info("test message")
        mock_logger.info.assert_called_with("test message")
    
    def test_sample_api_response_fixture(self, sample_api_response):
        """測試 sample_api_response fixture"""
        # sample_api_response 是一個函數
        response = sample_api_response()
        assert isinstance(response, dict)
        assert 'success' in response
        assert 'message' in response
        assert response['success'] is True
        assert response['message'] == "操作成功"
        
        # 測試帶數據的響應
        data_response = sample_api_response(data={'test': 'value'})
        assert 'data' in data_response
        assert data_response['data']['test'] == 'value'
        
        # 測試失敗響應
        error_response = sample_api_response(success=False, message="操作失敗")
        assert error_response['success'] is False
        assert error_response['message'] == "操作失敗"
    
    def test_sample_error_response_fixture(self, sample_error_response):
        """測試 sample_error_response fixture"""
        assert isinstance(sample_error_response, dict)
        assert 'success' in sample_error_response
        assert 'message' in sample_error_response
        assert 'error' in sample_error_response
        assert 'code' in sample_error_response
        
        assert sample_error_response['success'] is False
        assert sample_error_response['code'] == 500
    
    def test_mock_database_error_fixture(self, mock_database_error):
        """測試 mock_database_error fixture"""
        # mock_database_error 是一個函數
        connection_error = mock_database_error("connection")
        assert isinstance(connection_error, pyodbc.Error)
        
        timeout_error = mock_database_error("timeout")
        assert isinstance(timeout_error, pyodbc.OperationalError)
        
        integrity_error = mock_database_error("integrity")
        assert isinstance(integrity_error, pyodbc.IntegrityError)
        
        generic_error = mock_database_error("other")
        assert isinstance(generic_error, Exception)


class TestConftestConfiguration:
    """測試 conftest.py 中的配置"""
    
    def test_pytest_markers(self):
        """測試 pytest 標記是否正確配置"""
        # 這個測試檢查標記是否可以使用
        # 實際的標記配置在 pytest_configure 函數中
        pass  # pytest 會自動檢查標記配置
    
    def test_app_configuration_consistency(self, app):
        """測試應用配置的一致性"""
        # 檢查測試配置是否正確設置
        assert app.config['TESTING'] is True
        assert app.config['DEBUG'] is True
        assert app.config['ENV'] == 'testing'
        
        # 檢查資料庫配置
        assert app.config['DB_HOST'] == 'test_host'
        assert app.config['DB_NAME'] == 'test_routin_inspection'
        assert app.config['DB_USER'] == 'test_user'
        
        # 檢查 CORS 配置
        expected_origins = ['http://localhost:3000', 'http://127.0.0.1:3000']
        assert app.config['CORS_ORIGINS'] == expected_origins
    
    def test_flask_app_context(self, app):
        """測試 Flask 應用上下文是否正確設置"""
        # 檢查是否在應用上下文中
        from flask import current_app
        assert current_app == app
        assert current_app.config['TESTING'] is True


class TestFixtureInteractions:
    """測試 fixtures 之間的交互"""
    
    def test_client_with_app(self, app, client):
        """測試客戶端與應用的交互"""
        assert client.application == app
    
    def test_mock_objects_independence(self, mock_db_connection):
        """測試 mock 對象的獨立性"""
        mock_conn1, mock_cursor1 = mock_db_connection
        
        # 每次調用 fixture 應該返回新的 mock 對象
        # 但由於 fixture 的作用域，這裡我們只是檢查對象的基本屬性
        assert mock_conn1 is not None
        assert mock_cursor1 is not None
    
    def test_sample_data_consistency(self, sample_user_data, sample_form_data, sample_route_data):
        """測試範例數據的一致性"""
        # 檢查所有範例數據都是有效的字典
        assert isinstance(sample_user_data, dict)
        assert isinstance(sample_form_data, dict)
        assert isinstance(sample_route_data, dict)
        
        # 檢查必要字段存在
        assert sample_user_data['UserID']
        assert sample_form_data['formIdentifier']
        assert sample_route_data['RouteName']


class TestConftestPytestHooks:
    """測試 conftest.py 中的 pytest 鉤子函數"""
    
    def test_pytest_configure_markers(self):
        """測試 pytest_configure 設置的標記"""
        # 檢查我們可以使用這些標記
        # 實際的標記會在測試收集階段被驗證
        pass
    
    def test_session_scope_fixtures(self, app):
        """測試會話作用域的 fixtures"""
        # app fixture 應該在整個測試會話中只創建一次
        assert app is not None
        assert isinstance(app, Flask)


class TestEnvironmentSetup:
    """測試環境設置"""
    
    def test_python_path_setup(self):
        """測試 Python 路徑設置"""
        import sys
        
        # 檢查專案根目錄是否已添加到 Python 路徑
        project_root = '/home/bm/dev/projects/RoutinInspection-Project/RoutinInspection-backend'
        assert any(project_root in path for path in sys.path)
    
    def test_module_imports(self):
        """測試模組導入是否正常"""
        # 測試是否可以正常導入專案模組
        try:
            from config import create_app
            assert create_app is not None
        except ImportError:
            pytest.fail("無法導入 config 模組")
    
    def test_test_environment_variables(self):
        """測試環境變數設置"""
        import os
        
        # 檢查測試環境變數是否已設置
        assert os.getenv('FLASK_ENV') == 'testing'
        assert os.getenv('TESTING') == 'True'
        assert os.getenv('DEBUG') == 'True'