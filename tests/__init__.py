"""
測試模組

這個套件包含了巡檢系統後端的所有測試檔案。

測試結構：
- conftest.py: pytest 配置和共用 fixtures
- test_config.py: 配置相關測試
- test_route.py: 路線模組測試
- test_*.py: 其他模組測試

執行測試：
    pytest tests/                    # 執行所有測試
    pytest tests/test_route.py       # 執行特定模組測試
    pytest tests/ -v                 # 詳細輸出
    pytest tests/ --cov=models       # 包含覆蓋率報告
"""

# 測試版本
__version__ = "1.0.0"

# 測試套件資訊
__author__ = "RoutinInspection Development Team"
__description__ = "巡檢系統後端測試套件"

# 匯入常用的測試工具（可選）
import pytest
from unittest.mock import Mock, patch, MagicMock

# 設定測試環境的全域變數
TEST_DATABASE_NAME = "test_routin_inspection"
TEST_USER_PREFIX = "test_user_"
TEST_ROUTE_PREFIX = "test_route_"

# 測試資料常數
TEST_DATA = {
    "route": {
        "RouteName": "測試路線",
        "BindingTableId": 1,
        "BindingTableName": "test_table"
    },
    "user": {
        "UserName": "測試用戶",
        "UserID": "test_user_001",
        "Email": "test@example.com"
    }
}

# 匯出測試工具
__all__ = [
    "pytest",
    "Mock", 
    "patch", 
    "MagicMock",
    "TEST_DATABASE_NAME",
    "TEST_USER_PREFIX", 
    "TEST_ROUTE_PREFIX",
    "TEST_DATA"
]