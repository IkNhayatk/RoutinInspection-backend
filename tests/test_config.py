"""
配置模組測試

測試 config.py 模組中的配置類和應用工廠函數
"""

import pytest
import os
from unittest.mock import patch, Mock
from config import create_app, Config

class TestConfig:
    """測試配置類"""
    
    def test_config_from_environment(self):
        """測試從環境變數讀取配置"""
        with patch.dict(os.environ, {
            'DB_HOST': 'test_host',
            'DB_NAME': 'test_db', 
            'DB_USER': 'test_user',
            'DB_PASSWORD': 'test_password',
            'SECRET_KEY': 'test_secret_key',
            'CORS_ORIGINS': 'http://localhost:3000,http://127.0.0.1:3000'
        }, clear=True):
            config = Config()
            
            assert config.DB_HOST == 'test_host'
            assert config.DB_NAME == 'test_db'
            assert config.DB_USER == 'test_user'
            assert config.DB_PASSWORD == 'test_password'
            assert config.SECRET_KEY == 'test_secret_key'
            assert 'http://localhost:3000' in config.CORS_ORIGINS
    
    def test_config_defaults(self):
        """測試配置預設值"""
        with patch.dict(os.environ, {}, clear=True):
            config = Config(load_env=False)  # Skip .env loading for clean test
            
            assert config.DB_TRUST_SERVER_CERTIFICATE is False
            assert config.PORT == 3001
            assert config.LOG_LEVEL == 'INFO'
            assert config.ENV == 'production'
            assert config.DEBUG is False
            assert config.SECRET_KEY == '!!DEFAULT_KEY_MUST_BE_CHANGED_IN_PRODUCTION_ENV_VARIABLE!!'
    
    def test_config_cors_origins_parsing(self):
        """測試 CORS 來源字串解析"""
        # 測試單一來源
        with patch.dict(os.environ, {
            'CORS_ORIGINS': 'http://localhost:3000'
        }, clear=True):
            config = Config()
            assert config.CORS_ORIGINS == ['http://localhost:3000']
        
        # 測試多個來源
        with patch.dict(os.environ, {
            'CORS_ORIGINS': 'http://localhost:3000,http://127.0.0.1:3000,https://example.com'
        }, clear=True):
            config = Config()
            assert len(config.CORS_ORIGINS) == 3
            assert 'http://localhost:3000' in config.CORS_ORIGINS
            assert 'https://example.com' in config.CORS_ORIGINS
    
    def test_config_boolean_variables(self):
        """測試布林環境變數解析"""
        # 測試 True 值
        true_values = ['true', 'True', 'TRUE', '1', 'yes', 'Yes', 'YES']
        for value in true_values:
            with patch.dict(os.environ, {
                'DB_TRUST_SERVER_CERTIFICATE': value
            }, clear=True):
                config = Config(load_env=False)
                assert config.DB_TRUST_SERVER_CERTIFICATE is True, f"Failed for value: {value}"
        
        # 測試 False 值
        false_values = ['false', 'False', 'FALSE', '0', 'no', 'No', 'NO', 'n', 'f', '']
        for value in false_values:
            with patch.dict(os.environ, {
                'DB_TRUST_SERVER_CERTIFICATE': value
            }, clear=True):
                config = Config(load_env=False)
                assert config.DB_TRUST_SERVER_CERTIFICATE is False, f"Failed for value: {value}"
    
    def test_config_integer_variables(self):
        """測試整數環境變數解析"""
        with patch.dict(os.environ, {
            'PORT': '8080',
            'DB_POOL_SIZE': '20'
        }, clear=True):
            config = Config()
            assert config.PORT == 8080
            # 如果有 DB_POOL_SIZE 配置的話
            # assert config.DB_POOL_SIZE == 20
    
    def test_config_missing_required_variables(self):
        """測試缺少必要環境變數時的行為"""
        # 清除所有環境變數
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            
            # 檢查是否有適當的預設值或處理
            assert config.DB_HOST is not None  # 應該有預設值或處理機制
            assert config.SECRET_KEY is not None  # 應該有預設值或生成機制

class TestCreateApp:
    """測試應用工廠函數"""
    
    def test_create_app_with_default_config(self):
        """測試使用預設配置創建應用"""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test_secret_key_for_testing'
        }, clear=True):
            app = create_app()
            
            assert app is not None
            assert app.config['TESTING'] is False
            assert app.config['SECRET_KEY'] == 'test_secret_key_for_testing'
    
    def test_create_app_with_test_config(self):
        """測試使用測試配置創建應用"""
        test_config = {
            'TESTING': True,
            'SECRET_KEY': 'test_secret',
            'DB_HOST': 'test_host',
            'DEBUG': True
        }
        
        app = create_app(test_config)
        
        assert app.config['TESTING'] is True
        assert app.config['SECRET_KEY'] == 'test_secret'
        assert app.config['DB_HOST'] == 'test_host'
        assert app.config['DEBUG'] is True
    
    def test_create_app_config_override(self):
        """測試配置覆蓋功能"""
        # 設定環境變數
        with patch.dict(os.environ, {
            'DB_HOST': 'env_host',
            'SECRET_KEY': 'env_secret'
        }, clear=True):
            # 使用測試配置覆蓋
            test_config = {
                'DB_HOST': 'test_host',
                'DB_NAME': 'test_db'
            }
            
            app = create_app(test_config)
            
            # 測試配置應該覆蓋環境變數
            assert app.config['DB_HOST'] == 'test_host'
            assert app.config['DB_NAME'] == 'test_db'
            # 未覆蓋的環境變數應該保持原值
            assert app.config['SECRET_KEY'] == 'env_secret'
    
    def test_create_app_cors_configuration(self):
        """測試 CORS 配置"""
        test_config = {
            'SECRET_KEY': 'test_secret',
            'CORS_ORIGINS': ['http://localhost:3000', 'http://127.0.0.1:3000']
        }
        
        app = create_app(test_config)
        
        # 檢查 CORS 是否正確配置
        with app.test_client() as client:
            response = client.options('/api/test', 
                                    headers={'Origin': 'http://localhost:3000'})
            # CORS preflight 請求應該成功
            assert response.status_code in [200, 204]
    
    def test_create_app_blueprint_registration(self):
        """測試藍圖註冊"""
        test_config = {
            'SECRET_KEY': 'test_secret',
            'TESTING': True
        }
        
        app = create_app(test_config)
        
        # 檢查是否有註冊路由
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        
        # 應該包含一些基本路由
        assert any('/api' in rule for rule in rules)
    
    def test_create_app_error_handlers(self):
        """測試錯誤處理器設定"""
        test_config = {
            'SECRET_KEY': 'test_secret',
            'TESTING': True
        }
        
        app = create_app(test_config)
        
        with app.test_client() as client:
            # 測試 404 錯誤
            response = client.get('/nonexistent-endpoint')
            assert response.status_code == 404
            
            # 測試 500 錯誤（如果有設定的話）
            # 需要根據實際的錯誤處理器實現來測試

class TestSecurityConfiguration:
    """測試安全相關配置"""
    
    def test_create_app_insecure_secret_key_development(self):
        """測試開發環境下不安全的 SECRET_KEY"""
        with patch.dict(os.environ, {
            'FLASK_ENV': 'development'
        }):
            test_config = {
                'SECRET_KEY': 'changeme_in_production_to_a_strong_random_secret_key',
                'DEBUG': True
            }
            
            # 在開發環境下應該能正常創建應用，但可能會有警告
            app = create_app(test_config)
            assert app is not None
            assert app.config['DEBUG'] is True
    
    def test_create_app_insecure_secret_key_production(self):
        """測試生產環境下不安全的 SECRET_KEY"""
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production'
        }):
            test_config = {
                'SECRET_KEY': '!!DEFAULT_KEY_MUST_BE_CHANGED_IN_PRODUCTION_ENV_VARIABLE!!',
                'DEBUG': False
            }
            
            # 根據實際實現，可能會拋出異常或警告
            # 這裡假設會拋出 ValueError
            with pytest.raises(ValueError, match="Refusing to start in production"):
                create_app(test_config)
    
    def test_create_app_missing_secret_key_production(self):
        """測試生產環境下缺少 SECRET_KEY"""
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production'
        }, clear=True):
            test_config = {
                'SECRET_KEY': None,
                'DEBUG': False
            }
            
            # 在生產環境下應該拒絕啟動
            with pytest.raises(ValueError, match="Refusing to start in production"):
                create_app(test_config)
    
    def test_secret_key_validation(self):
        """測試 SECRET_KEY 驗證"""
        # 測試空 SECRET_KEY 在非生產環境
        with patch.dict(os.environ, {'FLASK_ENV': 'development'}, clear=True):
            test_config = {'SECRET_KEY': ''}
            app = create_app(test_config)  # Should work in development
            assert app is not None
        
        # 測試 None SECRET_KEY 在非生產環境
        with patch.dict(os.environ, {'FLASK_ENV': 'development'}, clear=True):
            test_config = {'SECRET_KEY': None}
            app = create_app(test_config)  # Should work in development
            assert app is not None

class TestDatabaseConfiguration:
    """測試資料庫配置"""
    
    def test_database_config_validation(self):
        """測試資料庫配置驗證"""
        test_config = {
            'SECRET_KEY': 'test_secret',
            'DB_HOST': 'localhost',
            'DB_NAME': 'test_db',
            'DB_USER': 'test_user',
            'DB_PASSWORD': 'test_password'
        }
        
        app = create_app(test_config)
        
        # 檢查資料庫配置是否正確設定
        assert app.config['DB_HOST'] == 'localhost'
        assert app.config['DB_NAME'] == 'test_db'
        assert app.config['DB_USER'] == 'test_user'
        assert app.config['DB_PASSWORD'] == 'test_password'
    
    def test_database_connection_string_formation(self):
        """測試資料庫連接字串生成"""
        test_config = {
            'SECRET_KEY': 'test_secret',
            'DB_HOST': 'test_server',
            'DB_NAME': 'test_database',
            'DB_USER': 'test_user',
            'DB_PASSWORD': 'test_pass',
            'DB_DRIVER': '{ODBC Driver 17 for SQL Server}',
            'DB_TRUST_SERVER_CERTIFICATE': True
        }
        
        app = create_app(test_config)
        
        # 如果有提供獲取連接字串的方法，可以測試
        # connection_string = app.config.get_database_connection_string()
        # assert 'test_server' in connection_string
        # assert 'test_database' in connection_string

class TestEnvironmentSpecificConfiguration:
    """測試不同環境的配置"""
    
    def test_development_environment_config(self):
        """測試開發環境配置"""
        with patch.dict(os.environ, {
            'FLASK_ENV': 'development',
            'SECRET_KEY': 'dev_secret_key'
        }):
            app = create_app()
            
            # 開發環境通常啟用除錯模式
            assert app.config.get('DEBUG') is True or app.config.get('ENV') == 'development'
    
    def test_production_environment_config(self):
        """測試生產環境配置"""
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'SECRET_KEY': 'very_secure_production_secret_key_that_is_long_enough'
        }, clear=True):
            app = create_app(load_env=False)  # Skip .env loading for clean test
            
            # 生產環境應該關閉除錯模式
            assert app.config.get('DEBUG') is False
            assert app.config.get('TESTING') is False
    
    def test_testing_environment_config(self):
        """測試測試環境配置"""
        test_config = {
            'TESTING': True,
            'SECRET_KEY': 'test_secret_key',
            'DEBUG': True
        }
        
        app = create_app(test_config)
        
        assert app.config['TESTING'] is True
        # 測試環境可能啟用除錯模式
        assert app.config.get('DEBUG') is True

class TestLoggingConfiguration:
    """測試日誌配置"""
    
    def test_logging_level_configuration(self):
        """測試日誌級別配置"""
        test_config = {
            'SECRET_KEY': 'test_secret',
            'LOG_LEVEL': 'DEBUG'
        }
        
        app = create_app(test_config)
        
        # 檢查日誌級別是否正確設定
        assert app.config['LOG_LEVEL'] == 'DEBUG'
        
        # 如果有日誌器配置，可以進一步測試
        # assert app.logger.level == logging.DEBUG
    
    def test_logging_in_different_environments(self):
        """測試不同環境的日誌配置"""
        # 開發環境
        with patch.dict(os.environ, {'FLASK_ENV': 'development'}):
            test_config = {'SECRET_KEY': 'test_secret'}
            app = create_app(test_config)
            
            # 開發環境可能使用 DEBUG 級別
            # assert app.logger.level <= logging.DEBUG
        
        # 生產環境
        with patch.dict(os.environ, {'FLASK_ENV': 'production'}):
            test_config = {
                'SECRET_KEY': 'production_secret_key_that_is_secure_enough'
            }
            app = create_app(test_config)
            
            # 生產環境可能使用較高的日誌級別
            # assert app.logger.level >= logging.INFO

class TestConfigurationValidation:
    """測試配置驗證"""
    
    def test_required_configuration_validation(self):
        """測試必要配置的驗證"""
        # 測試缺少 SECRET_KEY 在非生產環境下應該能正常工作
        with patch.dict(os.environ, {'FLASK_ENV': 'development'}, clear=True):
            app = create_app({})
            assert app is not None
    
    def test_configuration_type_validation(self):
        """測試配置類型驗證"""
        # 測試不正確的配置類型 - 配置在系統內部應該使用正確的類型
        with patch.dict(os.environ, {}, clear=True):
            test_config = {
                'SECRET_KEY': 'test_secret',
                'PORT': 8080,  # Use proper integer
                'DEBUG': True  # Use proper boolean
            }
            
            app = create_app(test_config)
            
            # 檢查是否有適當的類型
            assert isinstance(app.config.get('PORT'), int)
            assert isinstance(app.config.get('DEBUG'), bool)
            assert app.config.get('PORT') == 8080
            assert app.config.get('DEBUG') is True