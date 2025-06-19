# RoutinInspection Backend API

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.2.3-green.svg)
![SQL Server](https://img.shields.io/badge/SQL%20Server-Compatible-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

RoutinInspection 是一個基於 Flask 的企業級例行巡檢管理系統後端 API 服務，提供完整的用戶認證、動態表單管理和路由綁定功能。本專案採用現代化的 Python 開發實踐，提供安全、高效的 REST API 服務。

## 📋 專案概述

### 🎯 核心功能
- **🔐 用戶認證系統**：JWT token 認證、角色權限管理、密碼安全加密
- **📝 動態表單管理**：JSON schema 表單創建、自動資料表生成、驗證規則管理
- **🔄 路由綁定**：巡檢路線與表單關聯、動態資料管理
- **👥 用戶管理**：多層級權限控制、工作狀態追蹤、個人資料管理
- **🛡️ 安全機制**：CORS 保護、SQL 注入防護、bcrypt 密碼加密

### 🏗️ 技術架構
- **Web 框架**：Flask 2.2.3 with Blueprint 架構
- **資料庫**：SQL Server with pyodbc 連接
- **認證機制**：JWT (HS256) with 可配置過期時間
- **密碼加密**：bcrypt with salt
- **API 規範**：RESTful API 設計原則

## 📁 目錄結構

```
RoutinInspection-backend/
├── app.py                      # 🚀 應用程序入口點與 Blueprint 註冊
├── config.py                   # ⚙️ 應用程序工廠與配置管理
├── db.py                       # 🗄️ 資料庫連接與查詢工具
├── requirements.txt            # 📦 專案依賴套件
├── middleware/                 # 🛡️ 中間件模組
│   ├── __init__.py
│   └── auth.py                 # 認證與授權中間件
├── models/                     # 📊 資料模型與業務邏輯
│   ├── __init__.py
│   ├── form_schema.py          # 動態表單結構定義
│   ├── route.py                # 路由綁定模型
│   ├── table_manager.py        # 資料表管理
│   └── user.py                 # 用戶模型
├── routes/                     # 🛣️ API 端點定義
│   ├── __init__.py
│   ├── auth_routes.py          # 認證相關路由
│   ├── form_routes.py          # 表單管理路由
│   └── route_routes.py         # 路由綁定路由
├── tests/                      # 🧪 完整測試套件
│   ├── __init__.py
│   ├── conftest.py             # 測試配置與 fixtures
│   ├── test_config.py          # 配置測試
│   ├── test_form_schema.py     # 表單管理測試
│   ├── test_route.py           # 路由綁定測試
│   └── test_user.py            # 用戶管理測試
└── db_schema/                  # 📋 資料庫結構定義
    ├── CREATE_SysUser.sql      # 用戶資料表
    ├── CREATE_TableManager.sql # 表格管理資料表
    ├── CREATE_Routes.sql       # 路由資料表
    └── CREATE_DEMO_FormTable.sql # 示範表單資料表
```

## 🚀 快速開始

### 📋 系統需求
- **Python**: 3.8+ (推薦 3.9+)
- **資料庫**: SQL Server (2017+)
- **套件管理**: pip 21.0+
- **作業系統**: Windows 10+, macOS 10.14+, Ubuntu 18.04+

### ⚙️ 安裝步驟

1. **複製專案**
   ```bash
   git clone <repository-url>
   cd RoutinInspection-backend
   ```

2. **建立虛擬環境**
   ```bash
   # 建立虛擬環境
   python -m venv venv
   
   # 啟用虛擬環境
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **安裝依賴套件**
   ```bash
   # 升級 pip
   python -m pip install --upgrade pip
   
   # 安裝專案依賴
   pip install -r requirements.txt
   ```

4. **環境變數設定**
   
   建立 `.env` 檔案並設定以下變數：
   ```env
   # 🗄️ 資料庫配置
   DB_HOST=your-sql-server-host
   DB_NAME=RoutinInspection_dev
   DB_USER=your-db-username
   DB_PASSWORD=your-db-password
   DB_DRIVER={ODBC Driver 17 for SQL Server}
   DB_TRUST_SERVER_CERTIFICATE=yes
   
   # 🔐 安全配置
   SECRET_KEY=your-super-secure-secret-key-here
   CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
   
   # 🔧 應用程式配置
   FLASK_ENV=development
   FLASK_DEBUG=true
   PORT=3001
   ```

5. **資料庫初始化**
   ```bash
   # 執行資料庫結構建立 SQL 檔案
   # 請按順序執行 db_schema/ 目錄下的 SQL 檔案
   ```

6. **啟動開發伺服器**
   ```bash
   python app.py
   ```

7. **驗證安裝**
   
   開啟瀏覽器訪問：`http://localhost:3001/api/health` (如果有實作健康檢查端點)

### 🐳 Docker 部署 (可選)

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安裝系統依賴 (SQL Server ODBC driver)
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && echo "deb [arch=amd64] https://packages.microsoft.com/debian/10/prod buster main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*

# 複製並安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式檔案
COPY . .

# 設定環境變數
ENV FLASK_ENV=production
ENV PORT=3001

# 暴露端口
EXPOSE 3001

# 啟動命令
CMD ["python", "app.py"]
```

```bash
# 建置與執行 Docker 容器
docker build -t routin-inspection-backend .
docker run -p 3001:3001 --env-file .env routin-inspection-backend
```

## 📚 API 文檔

### 🔐 認證相關端點

#### POST /api/register
註冊新用戶
```json
// 請求
{
  "UserName": "張三",
  "UserID": "zhangsan001",
  "Password": "securePassword123",
  "PriorityLevel": 1,
  "Position": "巡檢員",
  "Department": "維護部",
  "Email": "zhangsan@company.com"
}

// 回應
{
  "success": true,
  "message": "用戶註冊成功",
  "user": {
    "ID": 1,
    "UserName": "張三",
    "UserID": "zhangsan001",
    "PriorityLevel": 1
  }
}
```

#### POST /api/login
用戶登入
```json
// 請求
{
  "user_id": "zhangsan001",
  "password": "securePassword123"
}

// 回應
{
  "success": true,
  "message": "登入成功",
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "ID": 1,
    "UserName": "張三",
    "PriorityLevel": 1
  }
}
```

#### 其他認證端點
- **POST /api/logout** - 用戶登出 (需要認證)
- **GET /api/users** - 獲取用戶列表 (需要優先級別 2+)
- **POST /api/users** - 創建新用戶 (需要優先級別 3)
- **PUT /api/users/{id}** - 更新用戶資訊 (需要優先級別 3)
- **DELETE /api/users/{id}** - 刪除用戶 (需要優先級別 3)
- **GET /api/profile** - 獲取當前用戶資料 (需要認證)
- **POST /api/change_password** - 更改密碼 (需要認證)

### 📝 表單管理端點

#### POST /api/forms
創建新表單
```json
// 請求
{
  "formIdentifier": "equipment_check",
  "formDisplayName": "設備巡檢表",
  "formDescription": "日常設備巡檢記錄表",
  "formSchema": {
    "elements": [
      {
        "type": "text",
        "name": "equipment_id",
        "label": "設備編號",
        "required": true
      }
    ]
  }
}
```

#### 其他表單端點
- **GET /api/forms** - 獲取表單列表 (支援分頁)
- **GET /api/forms/{id}** - 獲取特定表單
- **PUT /api/forms/{id}** - 更新表單
- **DELETE /api/forms/{id}** - 刪除表單
- **PUT /api/forms/{id}/mode** - 更新表單模式

### 🔄 路由綁定端點
- **GET /api/routes** - 獲取路由列表
- **POST /api/routes** - 創建新路由
- **PUT /api/routes/{id}** - 更新路由
- **DELETE /api/routes/{id}** - 刪除路由

## 🧪 測試指南

### 測試環境設定
```bash
# 安裝測試依賴 (已包含在 requirements.txt 中)
pip install pytest pytest-mock pytest-flask

# 設定測試環境變數
export FLASK_ENV=testing
```

### 執行測試
```bash
# 執行所有測試
pytest

# 執行特定測試檔案
pytest tests/test_user.py

# 顯示詳細資訊
pytest -v

# 產生測試覆蓋率報告
pytest --cov=. --cov-report=html

# 執行標記為 slow 的測試
pytest --runslow

# 執行整合測試
pytest -m integration
```

### 測試結構
```
tests/
├── conftest.py              # 測試配置與 fixtures
├── test_config.py           # 應用程式配置測試
├── test_form_schema.py      # 表單管理測試
├── test_route.py            # 路由綁定測試
└── test_user.py             # 用戶管理測試
```

## 🔧 開發指南

### 本地開發設定
```bash
# 啟用除錯模式
export FLASK_ENV=development
export FLASK_DEBUG=true

# 啟動開發伺服器
python app.py
```

### 程式碼規範
- 遵循 PEP 8 Python 程式碼風格指南
- 使用 docstring 為函數和類別添加文檔
- 實作適當的錯誤處理和日誌記錄
- 編寫對應的單元測試

### 資料庫遷移
```bash
# 手動執行 SQL 腳本
# 1. 執行 db_schema/CREATE_SysUser.sql
# 2. 執行 db_schema/CREATE_TableManager.sql
# 3. 執行 db_schema/CREATE_Routes.sql
# 4. 執行 db_schema/CREATE_DEMO_FormTable.sql
```

## 🚀 生產部署

### WSGI 伺服器部署
```bash
# 安裝 Gunicorn
pip install gunicorn

# 啟動生產伺服器
gunicorn -w 4 -b 0.0.0.0:3001 app:app

# 或使用配置檔案
gunicorn -c gunicorn.conf.py app:app
```

### 生產環境配置
```env
# 生產環境設定
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=your-production-secret-key
DB_HOST=production-db-host
# ... 其他生產配置
```

### Nginx 反向代理設定
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 🔒 安全考量

### 身份認證安全
- JWT token 預設 24 小時過期
- 密碼使用 bcrypt 加密儲存
- 支援多層級權限控制 (PriorityLevel 1-3)

### 資料庫安全
- 使用參數化查詢防止 SQL 注入
- 資料庫連接使用 SSL/TLS 加密
- 敏感資料不記錄在日誌中

### API 安全
- CORS 跨域請求保護
- 請求頻率限制 (可選)
- 輸入驗證和清理

## 🐛 常見問題

### 資料庫連接問題
```python
# 檢查 ODBC 驅動程式是否已安裝
import pyodbc
print(pyodbc.drivers())
```

### JWT Token 問題
```python
# 檢查 SECRET_KEY 是否正確設定
import os
print(os.getenv('SECRET_KEY'))
```

### CORS 問題
```python
# 檢查 CORS_ORIGINS 設定
from flask_cors import CORS
# 確保前端 URL 包含在 CORS_ORIGINS 中
```

## 📞 支援與貢獻

### 回報問題
- 使用 GitHub Issues 回報 bug
- 提供詳細的錯誤訊息和重現步驟
- 包含環境資訊 (Python 版本、作業系統等)

### 貢獻指南
1. Fork 此專案
2. 建立功能分支 (`git checkout -b feature/amazing-feature`)
3. 編寫測試並確保通過
4. 提交變更 (`git commit -m 'feat: add amazing feature'`)
5. 推送到分支 (`git push origin feature/amazing-feature`)
6. 開啟 Pull Request

### 開發環境
- 遵循現有的程式碼風格
- 編寫對應的測試
- 更新相關文檔
- 確保所有測試通過

## 📄 許可證

此專案採用 [MIT License](LICENSE) 授權條款。

---

## 📊 依賴套件

| 套件 | 版本 | 用途 |
|------|------|------|
| Flask | 2.2.3 | Web 框架 |
| Flask-CORS | 3.0.10 | 跨域請求處理 |
| python-dotenv | 1.0.0 | 環境變數管理 |
| pyodbc | 4.0.39 | SQL Server 連接 |
| PyJWT | 2.6.0 | JWT Token 處理 |
| bcrypt | 4.0.1 | 密碼加密 |
| pytest | 8.3.5 | 測試框架 |
| pytest-mock | 3.14.1 | 測試模擬 |
| pytest-flask | 1.3.0 | Flask 測試工具 |