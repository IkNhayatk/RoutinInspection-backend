from flask import Blueprint, request, jsonify
from models.route import get_route_by_id, get_all_routes, create_route, update_route, delete_route

# 導入資料庫連接
route_bp = Blueprint('route', __name__, url_prefix='/api')

@route_bp.route('/routes/<int:route_id>', methods=['GET'])
def get_route(route_id):
    """獲取特定巡檢路線"""
    try:
        route = get_route_by_id(route_id)
        if not route:
            return jsonify({
                "success": False,
                "message": "路線不存在"
            }), 404
        return jsonify({
            "success": True,
            "route": route
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"獲取路線失敗: {str(e)}"
        }), 500

@route_bp.route('/routes', methods=['GET'])
def get_routes():
    """獲取所有巡檢路線 (可選分頁、搜尋和模式)"""
    try:
        # 從查詢參數獲取分頁、搜尋條件和模式
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        search_term = request.args.get('search', None, type=str)
        mode = request.args.get('mode', None, type=str) # 根據需要調整 mode 的類型

        # 將參數傳遞給模型函數 get_all_routes
        # get_all_routes 函數 (在 models/route.py 中) 需要能夠處理這些參數
        # 並根據這些參數構建正確的 SQL 查詢
        routes_data = get_all_routes(page=page, limit=limit, search=search_term, mode=mode)

        # 假設 get_all_routes 返回一個包含 'routes' 列表和 'total' 總數的字典
        # 以便前端進行分頁。如果它只返回路線列表，您需要相應地調整。
        if isinstance(routes_data, dict) and 'routes' in routes_data and 'total_records' in routes_data:
            return jsonify({
                "success": True,
                "routes": routes_data['routes'],
                "pagination": {
                    "total_records": routes_data['total_records'],
                    "current_page": page,
                    "per_page": limit,
                    "total_pages": (routes_data['total_records'] + limit - 1) // limit # 計算總頁數
                }
            })
        elif isinstance(routes_data, list): # 如果只返回列表 (無分頁資訊)
             return jsonify({
                "success": True,
                "routes": routes_data
            })
        else: # 處理意外的返回類型
            current_app.logger.error(f"get_all_routes 返回了非預期的資料類型: {type(routes_data)}")
            return jsonify({
                "success": False,
                "message": "獲取路線列表時發生內部錯誤：資料格式不符"
            }), 500

    except Exception as e:
        # 使用 exc_info=True 來記錄完整的堆疊追蹤，這對於調試非常有用
        current_app.logger.error(f"在 get_routes 端點獲取路線列表時發生錯誤: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"獲取路線列表失敗: {str(e)}"
        }), 500

@route_bp.route('/routes', methods=['POST'])
def add_route():
    """新增巡檢路線"""
    data = request.get_json()
    try:
        new_route = create_route(data)
        return jsonify({
            "success": True,
            "message": "路線創建成功",
            "route": new_route
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"創建路線失敗: {str(e)}"
        }), 500

@route_bp.route('/routes/<int:route_id>', methods=['PUT'])
def update_route_data(route_id):
    """更新巡檢路線"""
    data = request.get_json()
    try:
        updated_route = update_route(route_id, data)
        if not updated_route:
            return jsonify({
                "success": False,
                "message": "路線不存在"
            }), 404
        return jsonify({
            "success": True,
            "message": "路線更新成功",
            "route": updated_route
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"更新路線失敗: {str(e)}"
        }), 500

@route_bp.route('/routes/<int:route_id>', methods=['DELETE'])
def delete_route_data(route_id):
    """刪除巡檢路線"""
    try:
        success = delete_route(route_id)
        if not success:
            return jsonify({
                "success": False,
                "message": "刪除路線失敗"
            }), 500
        return jsonify({
            "success": True,
            "message": "路線刪除成功"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"刪除路線失敗: {str(e)}"
        }), 500

