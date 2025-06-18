"""
測試 pytest 標記功能

測試 conftest.py 中定義的自定義標記是否正常工作
"""

import pytest


class TestPytestMarkers:
    """測試自定義 pytest 標記"""
    
    @pytest.mark.unit
    def test_unit_marker(self):
        """測試單元測試標記"""
        assert True
    
    @pytest.mark.integration  
    def test_integration_marker(self):
        """測試整合測試標記"""
        assert True
    
    @pytest.mark.api
    def test_api_marker(self):
        """測試 API 測試標記"""
        assert True
    
    @pytest.mark.slow
    def test_slow_marker(self):
        """測試慢速測試標記"""
        import time
        time.sleep(0.1)  # 模擬慢速操作
        assert True
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_multiple_markers(self):
        """測試多個標記組合"""
        assert True


class TestMarkerFiltering:
    """測試標記過濾功能"""
    
    @pytest.mark.unit
    def test_unit_only(self):
        """只在單元測試中運行"""
        assert True
    
    @pytest.mark.integration
    def test_integration_only(self):
        """只在整合測試中運行"""
        assert True
    
    def test_no_marker(self):
        """沒有標記的普通測試"""
        assert True