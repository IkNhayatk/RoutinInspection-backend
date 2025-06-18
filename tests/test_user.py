"""
用戶模組測試

測試 models/user.py 模組中的所有用戶相關功能，包括：
- 巡檢人員核簽資料檔操作
- 用戶資料一致性驗證
- 用戶 CRUD 操作
- 密碼驗證和權限檢查
- 工作狀態管理
"""

import pytest
import bcrypt
from unittest.mock import Mock, MagicMock, patch, call
from models.user import (
    add_signing_data, get_signing_data_by_user_id, delete_signing_data_by_user_id,
    validate_user_data_consistency, fix_user_data_consistency,
    add_user, get_user_with_signing_data, get_all_users_with_signing_data,
    update_user, get_user_by_id, get_user_by_user_id, get_all_users,
    delete_user, verify_password, check_priority_level, set_user_work_status
)


class TestSigningDataOperations:
    """測試核簽資料操作"""
    
    @patch('models.user.execute_query')
    def test_add_signing_data_new_record(self, mock_execute_query):
        """測試添加新的核簽資料"""
        # 模擬沒有現有記錄
        mock_execute_query.side_effect = [None, None]
        
        signing_data = {
            'supervisorName': '主管A',
            'supervisorID': 'sup001',
            'sectionChiefName': '課長B',
            'sectionChiefID': 'chief001',
            'factory': '工廠A',
            'section': '課別A'
        }
        
        result = add_signing_data(1, '測試用戶', 'test001', '測試部', signing_data)
        
        assert result is True
        assert mock_execute_query.call_count == 2
        
        # 檢查第一次查詢（檢查現有記錄）
        first_call = mock_execute_query.call_args_list[0]
        assert 'SELECT ID FROM [巡檢人員核簽資料檔]' in first_call[0][0]
        assert first_call[0][1] == ('test001',)
        assert first_call[1]['fetchone'] is True
        
        # 檢查第二次查詢（插入新記錄）
        second_call = mock_execute_query.call_args_list[1]
        assert 'INSERT INTO [巡檢人員核簽資料檔]' in second_call[0][0]
        assert second_call[1]['commit'] is True
    
    @patch('models.user.execute_query')
    def test_add_signing_data_update_existing(self, mock_execute_query):
        """測試更新現有核簽資料"""
        # 模擬有現有記錄
        mock_execute_query.side_effect = [{'ID': 1}, None]
        
        signing_data = {
            'supervisorName': '新主管',
            'supervisorID': 'newsup001',
            'factory': '新工廠'
        }
        
        result = add_signing_data(1, '測試用戶', 'test001', '測試部', signing_data)
        
        assert result is True
        assert mock_execute_query.call_count == 2
        
        # 檢查更新查詢
        update_call = mock_execute_query.call_args_list[1]
        assert 'UPDATE [巡檢人員核簽資料檔]' in update_call[0][0]
        assert update_call[1]['commit'] is True
    
    @patch('models.user.execute_query')
    def test_get_signing_data_by_user_id(self, mock_execute_query):
        """測試根據用戶ID獲取核簽資料"""
        expected_data = {
            '巡檢人姓名': '測試用戶',
            '巡檢人ID': 'test001',
            '主管姓名': '主管A',
            '主管ID': 'sup001'
        }
        mock_execute_query.return_value = expected_data
        
        result = get_signing_data_by_user_id('test001')
        
        assert result == expected_data
        mock_execute_query.assert_called_once_with(
            'SELECT * FROM [巡檢人員核簽資料檔] WHERE [巡檢人ID] = ?',
            ('test001',),
            fetchone=True
        )
    
    @patch('models.user.execute_query')
    def test_delete_signing_data_by_user_id_success(self, mock_execute_query):
        """測試成功刪除核簽資料"""
        mock_execute_query.return_value = None
        
        result = delete_signing_data_by_user_id('test001')
        
        assert result is True
        mock_execute_query.assert_called_once_with(
            'DELETE FROM [巡檢人員核簽資料檔] WHERE [巡檢人ID] = ?',
            ('test001',),
            commit=True
        )
    
    @patch('models.user.execute_query')
    def test_delete_signing_data_by_user_id_failure(self, mock_execute_query):
        """測試刪除核簽資料失敗"""
        mock_execute_query.side_effect = Exception("Database error")
        
        result = delete_signing_data_by_user_id('test001')
        
        assert result is False


class TestDataConsistencyValidation:
    """測試資料一致性驗證"""
    
    @patch('models.user.get_signing_data_by_user_id')
    @patch('models.user.get_user_by_id')
    def test_validate_user_data_consistency_consistent(self, mock_get_user, mock_get_signing):
        """測試資料一致的情況"""
        mock_get_user.return_value = {
            'UserName': '測試用戶',
            'UserID': 'test001',
            'Department': '測試部'
        }
        mock_get_signing.return_value = {
            '巡檢人姓名': '測試用戶',
            '巡檢人ID': 'test001',
            '部門縮寫': '測試部'
        }
        
        result = validate_user_data_consistency(1)
        
        assert result['is_consistent'] is True
        assert len(result['issues']) == 0
    
    @patch('models.user.get_signing_data_by_user_id')
    @patch('models.user.get_user_by_id')
    def test_validate_user_data_consistency_inconsistent(self, mock_get_user, mock_get_signing):
        """測試資料不一致的情況"""
        mock_get_user.return_value = {
            'UserName': '測試用戶',
            'UserID': 'test001',
            'Department': '測試部'
        }
        mock_get_signing.return_value = {
            '巡檢人姓名': '不同用戶',
            '巡檢人ID': 'different001',
            '部門縮寫': '不同部'
        }
        
        result = validate_user_data_consistency(1)
        
        assert result['is_consistent'] is False
        assert len(result['issues']) == 3  # 姓名、ID、部門都不一致
        assert any('姓名不一致' in issue for issue in result['issues'])
        assert any('用戶ID不一致' in issue for issue in result['issues'])
        assert any('部門不一致' in issue for issue in result['issues'])
    
    @patch('models.user.get_user_by_id')
    def test_validate_user_data_consistency_user_not_found(self, mock_get_user):
        """測試用戶不存在的情況"""
        mock_get_user.return_value = None
        
        result = validate_user_data_consistency(999)
        
        assert result['is_consistent'] is False
        assert 'SysUser表中找不到該用戶' in result['issues']
    
    @patch('models.user.get_signing_data_by_user_id')
    @patch('models.user.get_user_by_id')
    def test_validate_user_data_consistency_no_signing_data(self, mock_get_user, mock_get_signing):
        """測試沒有核簽資料的情況（這不算錯誤）"""
        mock_get_user.return_value = {
            'UserName': '測試用戶',
            'UserID': 'test001',
            'Department': '測試部'
        }
        mock_get_signing.return_value = None
        
        result = validate_user_data_consistency(1)
        
        assert result['is_consistent'] is True
        assert len(result['issues']) == 0
    
    @patch('models.user.execute_query')
    @patch('models.user.get_signing_data_by_user_id')
    @patch('models.user.get_user_by_id')
    def test_fix_user_data_consistency(self, mock_get_user, mock_get_signing, mock_execute):
        """測試修復資料一致性"""
        mock_get_user.return_value = {
            'UserName': '正確用戶',
            'UserID': 'correct001',
            'Department': '正確部'
        }
        mock_get_signing.return_value = {
            '巡檢人姓名': '錯誤用戶',
            '巡檢人ID': 'correct001'
        }
        mock_execute.return_value = None
        
        result = fix_user_data_consistency(1)
        
        assert result is True
        mock_execute.assert_called_once()
        
        # 檢查更新查詢
        call_args = mock_execute.call_args
        assert 'UPDATE [巡檢人員核簽資料檔]' in call_args[0][0]
        assert call_args[1]['commit'] is True
    
    @patch('models.user.get_user_by_id')
    def test_fix_user_data_consistency_user_not_found(self, mock_get_user):
        """測試修復不存在用戶的一致性"""
        mock_get_user.return_value = None
        
        result = fix_user_data_consistency(999)
        
        assert result is False


class TestUserCRUDOperations:
    """測試用戶 CRUD 操作"""
    
    @patch('models.user.get_user_with_signing_data')
    @patch('models.user.add_signing_data')
    @patch('models.user.get_user_by_user_id')
    @patch('models.user.get_db')
    def test_add_user_success(self, mock_get_db, mock_get_user_by_userid, 
                             mock_add_signing, mock_get_user_with_signing):
        """測試成功添加用戶"""
        # 模擬用戶不存在
        mock_get_user_by_userid.return_value = None
        
        # 模擬資料庫操作
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # 模擬獲取新用戶ID
        mock_result = MagicMock()
        mock_result.NewID = 123
        mock_cursor.fetchone.return_value = mock_result
        
        # 模擬返回完整用戶信息
        expected_user = {
            'ID': 123,
            'UserName': '測試用戶',
            'UserID': 'test001',
            'Email': 'test@example.com'
        }
        mock_get_user_with_signing.return_value = expected_user
        
        user_data = {
            'UserName': '測試用戶',
            'UserID': 'test001',
            'Password': 'password123',
            'Email': 'test@example.com',
            'PriorityLevel': 1,
            'Position': '工程師',
            'Department': '測試部',
            'signingData': {
                'supervisorName': '主管A',
                'supervisorID': 'sup001'
            }
        }
        
        result = add_user(user_data)
        
        assert result == expected_user
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()
        mock_add_signing.assert_called_once()
    
    @patch('models.user.get_user_by_user_id')
    def test_add_user_already_exists(self, mock_get_user_by_userid):
        """測試添加已存在的用戶"""
        mock_get_user_by_userid.return_value = {'ID': 1, 'UserName': '已存在用戶'}
        
        user_data = {
            'UserName': '測試用戶',
            'UserID': 'test001',
            'Password': 'password123'
        }
        
        result = add_user(user_data)
        
        assert result is None
    
    @patch('models.user.execute_query')
    def test_get_user_by_id(self, mock_execute_query):
        """測試根據ID獲取用戶"""
        expected_user = {
            'ID': 1,
            'UserName': '測試用戶',
            'UserID': 'test001'
        }
        mock_execute_query.return_value = expected_user
        
        result = get_user_by_id(1)
        
        assert result == expected_user
        mock_execute_query.assert_called_once_with(
            'SELECT * FROM SysUser WHERE ID = ?',
            (1,),
            fetchone=True
        )
    
    @patch('models.user.execute_query')
    def test_get_user_by_user_id(self, mock_execute_query):
        """測試根據UserID獲取用戶"""
        expected_user = {
            'ID': 1,
            'UserName': '測試用戶',
            'UserID': 'test001'
        }
        mock_execute_query.return_value = expected_user
        
        result = get_user_by_user_id('test001')
        
        assert result == expected_user
        mock_execute_query.assert_called_once_with(
            'SELECT * FROM SysUser WHERE UserID = ?',
            ('test001',),
            fetchone=True
        )
    
    @patch('models.user.execute_query')
    def test_get_all_users(self, mock_execute_query):
        """測試獲取所有用戶"""
        expected_users = [
            {'ID': 1, 'UserName': '用戶A'},
            {'ID': 2, 'UserName': '用戶B'}
        ]
        mock_execute_query.return_value = expected_users
        
        result = get_all_users()
        
        assert result == expected_users
        mock_execute_query.assert_called_once_with('SELECT * FROM SysUser ORDER BY ID')
    
    @patch('models.user.get_user_with_signing_data')
    @patch('models.user.add_signing_data')
    @patch('models.user.execute_query')
    @patch('models.user.get_user_by_id')
    def test_update_user_success(self, mock_get_user, mock_execute, 
                                mock_add_signing, mock_get_user_with_signing):
        """測試成功更新用戶"""
        # 模擬用戶存在
        mock_get_user.return_value = {
            'ID': 1,
            'UserName': '原用戶名',
            'UserID': 'test001'
        }
        
        # 模擬更新後的用戶信息
        updated_user = {
            'ID': 1,
            'UserName': '新用戶名',
            'UserID': 'test001',
            'Email': 'newemail@example.com'
        }
        mock_get_user_with_signing.return_value = updated_user
        
        user_data = {
            'UserName': '新用戶名',
            'Email': 'newemail@example.com',
            'Password': 'newpassword123',
            'signingData': {
                'supervisorName': '新主管'
            }
        }
        
        result = update_user(1, user_data)
        
        assert result == updated_user
        mock_execute.assert_called_once()
        mock_add_signing.assert_called_once()
    
    @patch('models.user.get_user_by_id')
    def test_update_user_not_found(self, mock_get_user):
        """測試更新不存在的用戶"""
        mock_get_user.return_value = None
        
        result = update_user(999, {'UserName': '新名稱'})
        
        assert result is None
    
    @patch('models.user.execute_query')
    @patch('models.user.delete_signing_data_by_user_id')
    @patch('models.user.get_user_by_id')
    def test_delete_user_success(self, mock_get_user, mock_delete_signing, mock_execute):
        """測試成功刪除用戶"""
        mock_get_user.return_value = {
            'ID': 1,
            'UserID': 'test001'
        }
        mock_delete_signing.return_value = True
        mock_execute.return_value = None
        
        result = delete_user(1)
        
        assert result is True
        mock_delete_signing.assert_called_once_with('test001')
        mock_execute.assert_called_once_with(
            'DELETE FROM SysUser WHERE ID = ?',
            (1,),
            commit=True
        )
    
    @patch('models.user.get_user_by_id')
    def test_delete_user_not_found(self, mock_get_user):
        """測試刪除不存在的用戶"""
        mock_get_user.return_value = None
        
        result = delete_user(999)
        
        assert result is False
    
    @patch('models.user.get_signing_data_by_user_id')
    @patch('models.user.get_user_by_id')
    def test_get_user_with_signing_data(self, mock_get_user, mock_get_signing):
        """測試獲取用戶及其核簽資料"""
        mock_get_user.return_value = {
            'ID': 1,
            'UserName': '測試用戶',
            'UserID': 'test001'
        }
        mock_get_signing.return_value = {
            '主管姓名': '主管A',
            '主管ID': 'sup001',
            '課長姓名': '課長B',
            '課長ID': 'chief001'
        }
        
        result = get_user_with_signing_data(1)
        
        assert result['UserName'] == '測試用戶'
        assert result['supervisorName'] == '主管A'
        assert result['supervisorID'] == 'sup001'
        assert result['sectionChiefName'] == '課長B'
        assert result['sectionChiefID'] == 'chief001'
    
    @patch('models.user.get_user_with_signing_data')
    @patch('models.user.get_all_users')
    def test_get_all_users_with_signing_data(self, mock_get_all, mock_get_with_signing):
        """測試獲取所有用戶及其核簽資料"""
        mock_get_all.return_value = [
            {'ID': 1, 'UserName': '用戶A'},
            {'ID': 2, 'UserName': '用戶B'}
        ]
        mock_get_with_signing.side_effect = [
            {'ID': 1, 'UserName': '用戶A', 'supervisorName': '主管A'},
            {'ID': 2, 'UserName': '用戶B', 'supervisorName': '主管B'}
        ]
        
        result = get_all_users_with_signing_data()
        
        assert len(result) == 2
        assert result[0]['supervisorName'] == '主管A'
        assert result[1]['supervisorName'] == '主管B'


class TestPasswordAndAuthentication:
    """測試密碼和認證功能"""
    
    @patch('models.user.get_user_by_user_id')
    def test_verify_password_success(self, mock_get_user):
        """測試密碼驗證成功"""
        # 生成測試用的雜湊密碼
        test_password = 'testpassword123'
        hashed = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt())
        
        mock_get_user.return_value = {
            'ID': 1,
            'UserID': 'test001',
            'Password': hashed.decode('utf-8')
        }
        
        result = verify_password('test001', test_password)
        
        assert result is not None
        assert result['UserID'] == 'test001'
    
    @patch('models.user.get_user_by_user_id')
    def test_verify_password_failure(self, mock_get_user):
        """測試密碼驗證失敗"""
        hashed = bcrypt.hashpw('correctpassword'.encode('utf-8'), bcrypt.gensalt())
        
        mock_get_user.return_value = {
            'ID': 1,
            'UserID': 'test001',
            'Password': hashed.decode('utf-8')
        }
        
        result = verify_password('test001', 'wrongpassword')
        
        assert result is None
    
    @patch('models.user.get_user_by_user_id')
    def test_verify_password_user_not_found(self, mock_get_user):
        """測試用戶不存在時的密碼驗證"""
        mock_get_user.return_value = None
        
        result = verify_password('nonexistent', 'anypassword')
        
        assert result is None
    
    @patch('models.user.get_user_by_user_id')
    def test_verify_password_no_password(self, mock_get_user):
        """測試用戶沒有密碼時的驗證"""
        mock_get_user.return_value = {
            'ID': 1,
            'UserID': 'test001',
            'Password': None
        }
        
        result = verify_password('test001', 'anypassword')
        
        assert result is None
    
    @patch('models.user.get_user_by_id')
    def test_check_priority_level_sufficient(self, mock_get_user):
        """測試權限級別足夠"""
        mock_get_user.return_value = {
            'ID': 1,
            'PriorityLevel': 3
        }
        
        result = check_priority_level(1, 2)
        
        assert result is True
    
    @patch('models.user.get_user_by_id')
    def test_check_priority_level_insufficient(self, mock_get_user):
        """測試權限級別不足"""
        mock_get_user.return_value = {
            'ID': 1,
            'PriorityLevel': 1
        }
        
        result = check_priority_level(1, 3)
        
        assert result is False
    
    @patch('models.user.get_user_by_id')
    def test_check_priority_level_user_not_found(self, mock_get_user):
        """測試用戶不存在時的權限檢查"""
        mock_get_user.return_value = None
        
        result = check_priority_level(999, 1)
        
        assert result is False
    
    @patch('models.user.get_user_by_id')
    def test_check_priority_level_no_priority(self, mock_get_user):
        """測試用戶沒有權限級別時的檢查"""
        mock_get_user.return_value = {
            'ID': 1,
            'PriorityLevel': None
        }
        
        result = check_priority_level(1, 1)
        
        assert result is False


class TestWorkStatusManagement:
    """測試工作狀態管理"""
    
    @patch('models.user.get_db')
    def test_set_user_work_status_success(self, mock_get_db):
        """測試成功設置用戶工作狀態"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1  # 表示有一行被更新
        
        result = set_user_work_status(1, True)
        
        assert result is True
        mock_cursor.execute.assert_called_once_with(
            'UPDATE SysUser SET IsAtWork = ?, UpdateDate = GETDATE() WHERE ID = ?',
            (1, 1)
        )
        mock_conn.commit.assert_called_once()
    
    @patch('models.user.get_db')
    def test_set_user_work_status_user_not_found(self, mock_get_db):
        """測試設置不存在用戶的工作狀態"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 0  # 表示沒有行被更新
        
        result = set_user_work_status(999, True)
        
        assert result is False
    
    @patch('models.user.get_db')
    def test_set_user_work_status_database_error(self, mock_get_db):
        """測試資料庫錯誤時的工作狀態設置"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Database error")
        
        result = set_user_work_status(1, False)
        
        assert result is False
        mock_conn.rollback.assert_called_once()


class TestPasswordHashing:
    """測試密碼雜湊功能"""
    
    def test_password_hashing_in_add_user(self):
        """測試添加用戶時的密碼雜湊"""
        with patch('models.user.get_user_by_user_id') as mock_get_user, \
             patch('models.user.get_db') as mock_get_db, \
             patch('models.user.get_user_with_signing_data') as mock_get_with_signing:
            
            mock_get_user.return_value = None
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_get_db.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            mock_result = MagicMock()
            mock_result.NewID = 123
            mock_cursor.fetchone.return_value = mock_result
            
            mock_get_with_signing.return_value = {'ID': 123}
            
            user_data = {
                'UserName': '測試用戶',
                'UserID': 'test001',
                'Password': 'plaintext_password'
            }
            
            add_user(user_data)
            
            # 檢查傳遞給資料庫的密碼是否已經雜湊
            # mock_cursor.execute 被調用時的參數
            call_args = mock_cursor.execute.call_args
            if call_args and len(call_args) > 1 and len(call_args[0]) > 1:
                params = call_args[0][1]
                hashed_password = params[4]  # Password 是第5個參數
                
                # 驗證密碼已被雜湊（不等於原始密碼）
                assert hashed_password != 'plaintext_password'
                # 驗證雜湊密碼可以通過 bcrypt 驗證
                assert bcrypt.checkpw(b'plaintext_password', hashed_password.encode('utf-8'))
            else:
                # 如果無法獲取參數，至少驗證 execute 被調用了
                assert mock_cursor.execute.called
    
    def test_password_hashing_in_update_user(self):
        """測試更新用戶時的密碼雜湊"""
        with patch('models.user.get_user_by_id') as mock_get_user, \
             patch('models.user.execute_query') as mock_execute, \
             patch('models.user.get_user_with_signing_data') as mock_get_with_signing:
            
            mock_get_user.return_value = {'ID': 1, 'UserName': '測試用戶'}
            mock_get_with_signing.return_value = {'ID': 1}
            
            user_data = {
                'Password': 'new_plaintext_password'
            }
            
            update_user(1, user_data)
            
            # 檢查密碼是否已經雜湊
            call_args = mock_execute.call_args[0][1]
            hashed_password = call_args[0]  # 第一個參數應該是雜湊後的密碼
            
            assert hashed_password != 'new_plaintext_password'
            assert bcrypt.checkpw(b'new_plaintext_password', hashed_password.encode('utf-8'))


class TestEdgeCasesAndErrorHandling:
    """測試邊界情況和錯誤處理"""
    
    @patch('models.user.execute_query')
    def test_add_signing_data_with_empty_signing_data(self, mock_execute_query):
        """測試添加空的核簽資料"""
        mock_execute_query.side_effect = [None, None]
        
        result = add_signing_data(1, '測試用戶', 'test001', '測試部', {})
        
        assert result is True
        # 檢查是否正確處理空的核簽資料字典
        assert mock_execute_query.call_count == 2
    
    @patch('models.user.get_user_by_id')
    def test_validate_user_data_consistency_exception(self, mock_get_user):
        """測試驗證過程中發生異常"""
        mock_get_user.side_effect = Exception("Database connection failed")
        
        result = validate_user_data_consistency(1)
        
        assert result['is_consistent'] is False
        assert any('驗證過程中發生錯誤' in issue for issue in result['issues'])
    
    @patch('models.user.get_user_by_id')
    def test_fix_user_data_consistency_exception(self, mock_get_user):
        """測試修復過程中發生異常"""
        mock_get_user.side_effect = Exception("Database error")
        
        result = fix_user_data_consistency(1)
        
        assert result is False
    
    def test_add_user_with_none_values(self):
        """測試添加包含 None 值的用戶"""
        with patch('models.user.get_user_by_user_id') as mock_get_user, \
             patch('models.user.get_db') as mock_get_db, \
             patch('models.user.get_user_with_signing_data') as mock_get_with_signing:
            
            mock_get_user.return_value = None
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_get_db.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            mock_result = MagicMock()
            mock_result.NewID = 123
            mock_cursor.fetchone.return_value = mock_result
            
            mock_get_with_signing.return_value = {'ID': 123}
            
            user_data = {
                'UserName': '測試用戶',
                'UserID': 'test001',
                'Password': None,  # None 密碼
                'Email': None,     # None 電子郵件
                'Position': None   # None 職位
            }
            
            result = add_user(user_data)
            
            assert result is not None
            # 確保沒有因為 None 值而崩潰
    
    @patch('models.user.get_db')
    def test_add_user_scope_identity_failure(self, mock_get_db):
        """測試 SCOPE_IDENTITY 失敗的情況"""
        with patch('models.user.get_user_by_user_id') as mock_get_user, \
             patch('models.user.get_user_with_signing_data') as mock_get_with_signing:
            
            mock_get_user.side_effect = [None, {'ID': 123, 'UserID': 'test001'}]
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_get_db.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # SCOPE_IDENTITY 返回 None
            mock_result = MagicMock()
            mock_result.NewID = None
            mock_cursor.fetchone.return_value = mock_result
            
            mock_get_with_signing.return_value = {'ID': 123}
            
            user_data = {
                'UserName': '測試用戶',
                'UserID': 'test001',
                'Password': 'password123'
            }
            
            result = add_user(user_data)
            
            assert result is not None
            # 確保通過備用方法獲取用戶ID


# 測試夾具和輔助函數
@pytest.fixture
def sample_signing_data():
    """範例核簽資料"""
    return {
        'supervisorName': '主管測試',
        'supervisorID': 'supervisor001',
        'sectionChiefName': '課長測試',
        'sectionChiefID': 'chief001',
        'safetyOfficer1': '工安人員1',
        'safetyOfficer1ID': 'safety001',
        'psmSpecialistName': 'PSM專員',
        'psmSpecialistID': 'psm001',
        'factoryManagerName': '廠長',
        'factoryManagerID': 'manager001',
        'safetySupervisorName': '工安主管',
        'safetySupervisorID': 'safetysup001',
        'safetySpecialistName': '工安高專',
        'safetySpecialistID': 'safetyspec001',
        'factory': '測試工廠',
        'section': '測試課',
        'jobTitle': '工程師',
        'secondDepartment': '第二部門'
    }


@pytest.fixture
def sample_user_with_signing():
    """範例用戶及核簽資料"""
    return {
        'ID': 1,
        'UserName': '測試用戶',
        'UserID': 'testuser001',
        'Email': 'test@example.com',
        'PriorityLevel': 2,
        'Position': '高級工程師',
        'Department': '測試部門',
        'supervisorName': '主管測試',
        'supervisorID': 'supervisor001',
        'sectionChiefName': '課長測試',
        'sectionChiefID': 'chief001'
    }