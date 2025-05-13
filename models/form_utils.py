import logging
from flask import current_app

def collect_items(element, items_list):
    """
    遞迴函數，收集 JSON 結構中所有有效的 ItemId。
    確保 ItemId 是整數且不重複。
    """
    if isinstance(element, dict):
        # 檢查是否為 Item 類型且包含 ItemId
        if element.get('ElmentType') == 'Item' and 'ItemId' in element:
            try:
                item_id = int(element['ItemId'])
                # 只有當 ItemId 是有效整數且尚未加入列表時才添加
                if item_id not in items_list:
                    items_list.append(item_id)
            except (ValueError, TypeError):
                 # 記錄無效的 ItemId 但繼續處理
                 current_app.logger.warning(f"Skipping invalid or non-integer ItemId: {element.get('ItemId')}")
        
        # 遞迴處理 'Elements' (如果是列表或字典)
        if 'Elements' in element:
            elements_value = element['Elements']
            if isinstance(elements_value, list):
                for sub_element in elements_value:
                    collect_items(sub_element, items_list)
            elif isinstance(elements_value, dict): # 處理 Elements 是單個物件的情況
                 collect_items(elements_value, items_list)
        
        # (可選) 如果需要遞迴處理字典中的其他值 (可能是巢狀結構)
        # for key, value in element.items():
        #     if key != 'Elements' and isinstance(value, (dict, list)):
        #          collect_items(value, items_list)

    # 如果元素本身是列表，遞迴處理列表中的每個元素
    elif isinstance(element, list):
        for sub_element in element:
            collect_items(sub_element, items_list)

    # 其他類型 (如字串、數字) 不包含 ItemId，直接忽略
