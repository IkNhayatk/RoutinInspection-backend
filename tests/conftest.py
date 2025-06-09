"""
pytest 配置檔案

這個檔案包含了所有測試的共用 fixtures 和配置。
pytest 會自動載入這個檔案中的 fixtures，讓所有測試檔案都可以使用。
"""

import pytest
import pyodbc
import os
import sys
from unittest.mock import Mock, MagicMock, patch
from flask import Flask

# 將專案根目錄加入 Python 路徑，確保可以正確匯入模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import create_app

@pytest.fixture(scope="session")
def app():
    """
    創建測試用的 Flask 應用
    scope="session" 表示整個測試會話只創建一次應用實例
    """
    test_config = {
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key-for-testing-only-do-not-use-in-production',
        'DB_HOST': 'test_host',
        'DB_NAME': 'test_routin_inspection',
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_password',
        'DB_DRIVER': '{ODBC Driver 17 for SQL Server}',
        'DB_TRUST_SERVER_CERTIFICATE': False,
        'CORS_ORIGINS': ['http://localhost:3000', 'http://127.0.0.1:3000'],
        'DEBUG': True,
        'ENV': 'testing',
        'PORT': 5000,
        'LOG_LEVEL': 'DEBUG'
    }
    
    app = create_app(test_config)
    
    # 創建應用上下文
    with app.app_context():
        yield app

@pytest.fixture
def client(app):
    """
    創建測試客戶端
    用於測試 HTTP 端點
    """
    return app.test_client()

@pytest.fixture
def runner(app):
    """
    創建 CLI 測試運行器
    用於測試命令列介面
    """
    return app.test_cli_runner()

@pytest.fixture
def mock_db_connection():
    """
    模擬資料庫連接
    返回 (mock_connection, mock_cursor) 元組
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    
    # 設定 cursor 的基本行為
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.commit = MagicMock()
    mock_conn.rollback = MagicMock()
    mock_conn.close = MagicMock()
    
    # 設定 cursor 的方法
    mock_cursor.close = MagicMock()
    mock_cursor.execute = MagicMock()
    mock_cursor.fetchone = MagicMock(return_value=None)
    mock_cursor.fetchall = MagicMock(return_value=[])
    mock_cursor.fetchmany = MagicMock(return_value=[])
    mock_cursor.rowcount = 1
    mock_cursor.description = None
    
    return mock_conn, mock_cursor

@pytest.fixture
def mock_db_cursor(mock_db_connection):
    """
    只返回模擬的 cursor 物件
    用於只需要 cursor 的測試
    """
    _, mock_cursor = mock_db_connection
    return mock_cursor

@pytest.fixture
def sample_form_data():
    """
    範例表單數據
    用於測試表單相關功能
    """
    return {
        'formIdentifier': 'test_form_001',
        'formDisplayName': '測試表單A',
        'formJson': {
            "Elements": [
                {"ElmentType": "Item", "ItemId": "1"},
                {"ElmentType": "Item", "ItemId": "2"},
                {"ElmentType": "Group", "Elements": [
                    {"ElmentType": "Item", "ItemId": "3"},
                    {"ElmentType": "Item", "ItemId": "4"}
                ]}
            ]
        },
        'mode': 1,
        'isActive': True
    }

@pytest.fixture
def sample_form_data_list():
    """
    多個範例表單數據
    用於測試批量操作
    """
    return [
        {
            'formIdentifier': 'test_form_001',
            'formDisplayName': '測試表單A',
            'formJson': {
                "Elements": [
                    {"ElmentType": "Item", "ItemId": "1"},
                    {"ElmentType": "Item", "ItemId": "2"}
                ]
            },
            'mode': 1,
            'isActive': True
        },
        {
            'formIdentifier': 'test_form_002',
            'formDisplayName': '測試表單B',
            'formJson': {
                "Elements": [
                    {"ElmentType": "Item", "ItemId": "10"},
                    {"ElmentType": "Item", "ItemId": "11"}
                ]
            },
            'mode': 0,
            'isActive': False
        }
    ]

@pytest.fixture
def sample_route_data():
    """
    範例路線數據
    用於測試路線相關功能
    """
    return {
        'RouteName': '測試路線A',
        'BindingTableId': 100,
        'BindingTableName': 'test_binding_table'
    }

@pytest.fixture
def sample_route_data_list():
    """
    多個範例路線數據
    用於測試批量操作
    """
    return [
        {
            'RouteName': '測試路線A',
            'BindingTableId': 100,
            'BindingTableName': 'test_table_a'
        },
        {
            'RouteName': '測試路線B',
            'BindingTableId': 200,
            'BindingTableName': 'test_table_b'
        },
        {
            'RouteName': '測試路線C',
            'BindingTableId': None,
            'BindingTableName': None
        }
    ]

@pytest.fixture
def sample_routes_db_result():
    """
    範例路線資料庫查詢結果
    模擬從資料庫查詢回來的元組格式
    """
    return [
        (1, '路線A', 10, 'table_a'),
        (2, '路線B', 20, 'table_b'),
        (3, '路線C', None, None),
        (4, '路線D', 30, 'table_d')
    ]

@pytest.fixture
def sample_user_data():
    """
    範例用戶數據
    用於測試用戶相關功能
    """
    return {
        'UserName': '測試用戶',
        'UserID': 'testuser001',
        'Password': 'TestPassword123!',
        'Email': 'testuser@example.com',
        'PriorityLevel': 1,
        'Position': '測試工程師',
        'Department': '測試部門'
    }

@pytest.fixture
def sample_user_data_list():
    """
    多個範例用戶數據
    """
    return [
        {
            'UserName': '測試用戶A',
            'UserID': 'testusera',
            'Password': 'TestPasswordA123!',
            'Email': 'testusera@example.com',
            'PriorityLevel': 1,
            'Position': '高級工程師',
            'Department': '開發部門'
        },
        {
            'UserName': '測試用戶B',
            'UserID': 'testuserb',
            'Password': 'TestPasswordB123!',
            'Email': 'testuserb@example.com',
            'PriorityLevel': 2,
            'Position': '初級工程師',
            'Department': '測試部門'
        }
    ]

@pytest.fixture
def auth_headers():
    """
    認證標頭生成器
    用於測試需要認證的 API 端點
    """
    def _create_auth_headers(token="test-jwt-token-12345"):
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    return _create_auth_headers

@pytest.fixture
def mock_jwt_token():
    """
    模擬 JWT token
    """
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.payload"

@pytest.fixture
def mock_current_user():
    """
    模擬當前登入用戶
    """
    return {
        'UserID': 'testuser001',
        'UserName': '測試用戶',
        'Email': 'testuser@example.com',
        'PriorityLevel': 1,
        'Position': '測試工程師',
        'Department': '測試部門'
    }

@pytest.fixture
def pagination_params():
    """
    分頁參數
    用於測試分頁功能
    """
    return {
        'page': 1,
        'limit': 10,
        'search': None,
        'mode': None
    }

@pytest.fixture
def search_pagination_params():
    """
    帶搜尋的分頁參數
    """
    return {
        'page': 1,
        'limit': 5,
        'search': '測試',
        'mode': '1'
    }

@pytest.fixture
def mock_logger():
    """
    模擬 Flask logger
    用於測試日誌記錄
    """
    mock_logger = Mock()
    mock_logger.debug = Mock()
    mock_logger.info = Mock()
    mock_logger.warning = Mock()
    mock_logger.error = Mock()
    mock_logger.critical = Mock()
    return mock_logger

@pytest.fixture
def sample_api_response():
    """
    範例 API 響應格式
    """
    def _create_response(success=True, message="操作成功", data=None):
        response = {
            'success': success,
            'message': message
        }
        if data is not None:
            response['data'] = data
        return response
    return _create_response

@pytest.fixture
def sample_error_response():
    """
    範例錯誤響應格式
    """
    return {
        'success': False,
        'message': '操作失敗',
        'error': 'Internal Server Error',
        'code': 500
    }

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """
    自動設定測試環境
    autouse=True 表示每個測試都會自動使用這個 fixture
    """
    # 設定測試環境變數
    test_env_vars = {
        'FLASK_ENV': 'testing',
        'TESTING': 'True',
        'DEBUG': 'True'
    }
    
    for key, value in test_env_vars.items():
        monkeypatch.setenv(key, value)

@pytest.fixture
def mock_database_error():
    """
    模擬資料庫錯誤
    """
    def _create_db_error(error_type="connection", message="Database connection failed"):
        if error_type == "connection":
            return pyodbc.Error(message)
        elif error_type == "timeout":
            return pyodbc.OperationalError(message)
        elif error_type == "integrity":
            return pyodbc.IntegrityError(message)
        else:
            return Exception(message)
    return _create_db_error

# pytest 鉤子函數
def pytest_configure(config):
    """
    pytest 配置鉤子
    在測試開始前執行
    """
    # 設定自定義標記
    config.addinivalue_line(
        "markers", "slow: 標記測試為慢速測試"
    )
    config.addinivalue_line(
        "markers", "integration: 標記測試為整合測試"
    )
    config.addinivalue_line(
        "markers", "unit: 標記測試為單元測試"
    )
    config.addinivalue_line(
        "markers", "api: 標記測試為 API 測試"
    )

def pytest_collection_modifyitems(config, items):
    """
    修改測試項目收集
    可以根據標記自動跳過某些測試
    """
    # 如果沒有指定 --runslow，則跳過慢速測試
    if not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="需要 --runslow 選項來執行")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

def pytest_addoption(parser):
    """
    添加命令列選項
    """
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="執行標記為 slow 的測試"
    )
    parser.addoption(
        "--runintegration",
        action="store_true", 
        default=False,
        help="執行整合測試"
    )

# 測試會話開始和結束的鉤子
@pytest.fixture(scope="session", autouse=True)
def setup_test_session():
    """
    測試會話設定
    在整個測試會話開始前執行
    """
    print("\n=== 開始測試會話 ===")
    # 在這裡可以進行全域設定，例如創建測試資料庫、初始化測試數據等
    
    yield  # 測試執行
    
    print("\n=== 結束測試會話 ===")
    # 在這裡可以進行清理工作，例如刪除測試資料庫、清理測試檔案等

@pytest.fixture(autouse=True)
def setup_test_function():
    """
    每個測試函數的設定
    在每個測試函數執行前後執行
    """
    # 測試前設定
    yield
    # 測試後清理
    pass