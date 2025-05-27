# RoutinInspection 後端 API

RoutinInspection 是一個基於 Flask 的後端 API 服務，旨在提供用戶認証和表單管理功能。本專案使用 Python 開發，並使用 Flask 框架作為 Web 應用程序基礎。

## 專案概述

RoutinInspection 後端 API 提供以下主要功能：
- **用戶認証**：包括用戶註冊、登入、登出、用戶資料管理和密碼更改。
- **表單管理**：支援表單的創建、查詢、更新和刪除，以及表單模式的設定。

## 目錄結構

```
RoutinInspection-backend/
├── app.py                  # 應用程序入口點
├── config.py               # 應用程序配置
├── db.py                   # 資料庫初始化和連接管理
├── middleware/             # 中間件模組
│   └── auth.py             # 認証中間件
├── models/                 # 資料模型
│   ├── form.py             # 表單模型
│   ├── form_schema.py      # 表單結構定義
│   ├── form_utils.py       # 表單相關工具函數
│   ├── table_manager.py    # 資料表管理
│   └── user.py             # 用戶模型
├── routes/                 # API 路由定義
│   ├── auth_routes.py      # 認証相關路由
│   └── form_routes.py      # 表單相關路由
└── requirements.txt        # 專案依賴套件
```

## 安裝指南

### 環境需求
- Python 3.8 或更高版本
- pip 套件管理器

### 安裝步驟
1. 克隆此儲存庫到本地：
   ```
   git clone <repository-url>
   cd RoutinInspection-backend
   ```
2. 創建並啟用虛擬環境：
   ```
   python -m venv venv
   source venv/bin/activate  # 在 Windows 上使用：venv\Scripts\activate
   ```
3. 安裝依賴套件：
   ```
   pip install -r requirements.txt
   ```
4. 設定環境變數：
   - 創建一個 `.env` 檔案，參考以下內容設定必要的環境變數：
     ```
     DB_HOST=<your-database-host>
     DB_NAME=<your-database-name>
     DB_USER=<your-database-user>
     DB_PASSWORD=<your-database-password>
     DB_DRIVER=<your-database-driver>
     DB_TRUST_SERVER_CERTIFICATE=<yes/no>
     SECRET_KEY=<your-secret-key>
     CORS_ORIGINS=<allowed-origins>
     FLASK_ENV=development
     FLASK_DEBUG=true
     PORT=5000
     ```
5. 啟動應用程序：
   ```
   python app.py
   ```

應用程序將在 `http://localhost:5000` 上運行（或根據您的 `PORT` 設定）。

## 使用說明

### API 端點

#### 認証相關端點
- **POST /api/register** - 註冊新用戶
  - 請求體：`{ "UserName": "string", "UserID": "string", "Password": "string", "PriorityLevel": number }`
  - 回應：`{ "success": boolean, "message": "string", "user": object }`
- **POST /api/login** - 用戶登入
  - 請求體：`{ "user_id": "string", "password": "string" }`
  - 回應：`{ "success": boolean, "message": "string", "token": "string", "user": object }`
- **POST /api/logout** - 用戶登出（需要認証）
  - 回應：`{ "success": boolean, "message": "string" }`
- **GET /api/users** - 獲取所有用戶列表（需要優先級別 2）
  - 回應：`{ "success": boolean, "users": array }`
- **POST /api/users** - 創建新用戶（需要優先級別 3）
  - 請求體：`{ "UserName": "string", "UserID": "string", "Password": "string", "PriorityLevel": number }`
  - 回應：`{ "success": boolean, "message": "string", "user": object }`
- **PUT /api/users/<id>** - 更新用戶信息（需要優先級別 3）
  - 請求體：`{ "UserName": "string", "PriorityLevel": number, ... }`
  - 回應：`{ "success": boolean, "message": "string", "user": object }`
- **DELETE /api/users/<id>** - 刪除用戶（需要優先級別 3）
  - 回應：`{ "success": boolean, "message": "string" }`
- **GET /api/profile** - 獲取當前用戶資料（需要認証）
  - 回應：`{ "success": boolean, "user": object }`
- **POST /api/change_password** - 更改密碼（需要認証）
  - 請求體：`{ "old_password": "string", "new_password": "string" }`
  - 回應：`{ "success": boolean, "message": "string" }`

#### 表單相關端點
- **POST /api/forms** - 創建新表單
  - 請求體：`{ "formIdentifier": "string", "formDisplayName": "string", ... }`
  - 回應：`{ "success": boolean, "message": "string", "form": object }`
- **GET /api/forms** - 獲取所有表單（支援分頁）
  - 查詢參數：`page` (預設 1), `limit` (預設 10)
  - 回應：`{ "success": boolean, "forms": array, "total": number }`
- **GET /api/forms/<id>** - 獲取特定表單
  - 回應：`{ "success": boolean, "form": object }`
- **PUT /api/forms/<id>** - 更新表單數據
  - 請求體：`{ "formDisplayName": "string", ... }`
  - 回應：`{ "success": boolean, "message": "string", "form": object }`
- **DELETE /api/forms/<id>** - 刪除表單
  - 回應：`{ "success": boolean, "message": "string" }`
- **PUT /api/forms/<id>/mode** - 更新表單模式
  - 請求體：`{ "mode": number (0 or 1) }`
  - 回應：`{ "success": boolean, "message": "string", "mode": number }`

### 資料庫配置
資料庫連接參數從環境變數中讀取，請確保在 `.env` 檔案中正確設定 `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_DRIVER` 和 `DB_TRUST_SERVER_CERTIFICATE`。

### 安全配置
- **SECRET_KEY**：用於 JWT 令牌生成和會話管理，必須在環境變數中設定一個安全的隨機值。
- **CORS_ORIGINS**：設定允許跨域請求的來源，預設為 `http://localhost:3000`，可在環境變數中修改。

## 開發與測試
- 設定 `FLASK_ENV=development` 和 `FLASK_DEBUG=true` 以啟用除錯模式。
- 使用不同的配置創建測試實例：`app = create_app(test_config={'DEBUG': True, 'PORT': 5001})`。

## 部署注意事項
- 生產環境中，應使用 WSGI 伺服器（如 Gunicorn）而非 Flask 內建的開發伺服器。
- 確保 `SECRET_KEY` 已安全設定，否則應用程序將拒絕啟動。
- 檢查 CORS 配置是否符合您的前端應用程序需求。

## 貢獻指南
歡迎提交問題和拉取請求，請遵循以下步驟：
1. Fork 此儲存庫
2. 創建您的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟一個拉取請求

## 許可證
此專案採用 [MIT](LICENSE) 授權條款。