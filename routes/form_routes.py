from flask import Blueprint, request, jsonify
# Update imports to use the new modular structure
from models.table_manager import add_form, get_all_forms, get_form_by_id, update_form, delete_form, update_form_mode, search_department
# If you need any schema or utils functions, import them like:
# from models.form_schema import create_form_table, rename_and_update_form_table
# from models.form_utils import collect_items

# 創建藍圖
form_bp = Blueprint('forms', __name__, url_prefix='/api')

@form_bp.route('/forms', methods=['POST'])
def create_form():
    """創建新表單"""
    data = request.get_json()
    
    # 驗證必要字段
    required_fields = ['formIdentifier', 'formDisplayName']
    for field in required_fields:
        if field not in data:
            return jsonify({
                "success": False,
                "message": f"缺少必要字段: {field}"
            }), 400
    
    try:
        new_form = add_form(data)
        
        if not new_form:
            return jsonify({
                "success": False,
                "message": "創建表單失敗"
            }), 400
        
        return jsonify({
            "success": True,
            "message": "表單創建成功",
            "form": new_form
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"創建表單失敗: {str(e)}"
        }), 500

@form_bp.route('/forms', methods=['GET'])
def get_forms():
    """獲取所有表單，支援分頁"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        result = get_all_forms(page=page, limit=limit)
        return jsonify({
            "success": True,
            "forms": result["forms"],
            "total": result["total"]
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"獲取表單列表失敗: {str(e)}"
        }), 500

# 將原本的路由改名，避免衝突
@form_bp.route('/search-department', methods=['GET'])
def search_department_forms():
    """根據部門代碼搜尋表單"""
    code = request.args.get('code')
    if not code:
        return jsonify({
            "success": False,
            "message": "缺少部門代碼參數"
        }), 400
    
    try:
        forms = search_department(code)
        return jsonify({
            "success": True,
            "forms": forms,  # 使用複數形式
            "total": len(forms)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"搜尋表單失敗: {str(e)}"
        }), 500

# 保留原本的 get_form 但改用 form_id
@form_bp.route('/forms/<int:form_id>', methods=['GET'])
def get_form_by_id(form_id):
    """根據 ID 獲取特定表單"""
    try:
        form = get_form_by_id(form_id)
        if not form:
            return jsonify({
                "success": False,
                "message": "表單不存在"
            }), 404
        return jsonify({
            "success": True,
            "form": form
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"獲取表單失敗: {str(e)}"
        }), 500

@form_bp.route('/forms/<int:form_id>', methods=['PUT'])
def update_form_data(form_id):
    """更新表單數據"""
    data = request.get_json()
    try:
        updated_form = update_form(form_id, data)
        if not updated_form:
            return jsonify({
                "success": False,
                "message": "表單不存在"
            }), 404
        return jsonify({
            "success": True,
            "message": "表單更新成功",
            "form": updated_form
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"更新表單失敗: {str(e)}"
        }), 500

@form_bp.route('/forms/<int:form_id>', methods=['DELETE'])
def delete_form_data(form_id):
    """刪除表單"""
    try:
        success = delete_form(form_id)
        if not success:
            return jsonify({
                "success": False,
                "message": "刪除表單失敗"
            }), 500
        return jsonify({
            "success": True,
            "message": "表單刪除成功"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"刪除表單失敗: {str(e)}"
        }), 500

@form_bp.route('/forms/<int:form_id>/mode', methods=['PUT'])
def update_form_mode_data(form_id):
    """更新表單模式"""
    data = request.get_json()
    mode = data.get('mode')
    if mode not in [0, 1]:
        return jsonify({
            "success": False,
            "message": "無效的模式值"
        }), 400
    try:
        success = update_form_mode(form_id, mode)
        if not success:
            return jsonify({
                "success": False,
                "message": "更新表單模式失敗"
            }), 404
        return jsonify({
            "success": True,
            "message": "表單模式更新成功",
            "mode": mode
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"更新表單模式失敗: {str(e)}"
        }), 500