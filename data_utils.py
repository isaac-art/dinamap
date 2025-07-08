import re
import os
import json
import time
from uuid import uuid4 as u4
from fastapi.responses import JSONResponse

def validate_uid(uid):
    if not uid: return False, "UID cannot be empty"
    uid_str = str(uid)
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    if not uuid_pattern.match(uid_str): return False, "Invalid UID format"
    return True, uid_str


def validate_key(key):
    if not key or not isinstance(key, str):
        return False, "Key must be a non-empty string"
    if not re.match(r'^[a-zA-Z0-9_]+$', key):
        return False, "Key can only contain letters, numbers, and underscores"
    forbidden_patterns = [
        r'\.\.',  # Directory traversal
        r'<script',  # XSS
        r'javascript:',  # XSS
        r'data:',  # Data URI injection
        r'vbscript:',  # VBScript injection
    ]
    for pattern in forbidden_patterns:
        if re.search(pattern, key, re.IGNORECASE):
            return False, f"Key contains forbidden pattern: {pattern}"
    return True, key


def validate_value(value):
    if value is None: return False, "Value cannot be None"
    value_str = str(value)
    if len(value_str) > 10000:  # 10KB limit
        return False, "Value too large (max 10KB)"

    if isinstance(value, str):
        forbidden_patterns = [
            r'<script[^>]*>',  # XSS
            r'javascript:',  # XSS
            r'data:',  # Data URI injection
            r'vbscript:',  # VBScript injection
            r'<iframe[^>]*>',  # iframe injection
            r'<object[^>]*>',  # object injection
            r'<embed[^>]*>',  # embed injection
        ]
        for pattern in forbidden_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return False, f"Value contains forbidden pattern: {pattern}"
    
    if isinstance(value, list):
        if len(value) > 100:
            return False, "List too large (max 100 items)"
        
        for i, item in enumerate(value):
            if not isinstance(item, (str, int, float, bool)):
                return False, f"Invalid item type at index {i}"
            is_valid, error = validate_value(item)
            if not is_valid:
                return False, f"Invalid item at index {i}: {error}"
    
    if isinstance(value, dict):
        if len(value) > 50:  # Limit dict size
            return False, "Dictionary too large (max 50 items)"
        
        for k, v in value.items():
            is_valid, error = validate_key(k)
            if not is_valid:
                return False, f"Invalid key '{k}': {error}"
            is_valid, error = validate_value(v)
            if not is_valid:
                return False, f"Invalid value for key '{k}': {error}"
    
    return True, value


def update_json(uid, key, value):
    try:
        is_valid, error = validate_uid(uid)
        if not is_valid: raise ValueError(f"Invalid UID: {error}")
        is_valid, error = validate_key(key)
        if not is_valid: raise ValueError(f"Invalid key: {error}")
        is_valid, error = validate_value(value)
        if not is_valid: raise ValueError(f"Invalid value: {error}")
        
        if os.path.exists("main.json"):
            with open("main.json", 'r') as f:
                data = json.load(f)
        else:  data = {}
        
        if not isinstance(data, dict): raise ValueError("Corrupted JSON file: root must be an object")
        
        if str(uid) not in data: data[str(uid)] = {}
        
        if not isinstance(data[str(uid)], dict): data[str(uid)] = {}
        
        data[str(uid)][key] = value
        json.dumps(data)
        with open("main.json", 'w') as f: json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error updating JSON: {e}")
        raise


def generate_stats():
    """Generate statistics on saved items and avatars by popularity"""
    try:
        # Load data from JSON file
        if not os.path.exists("main.json"):
            return {
                "saved_items": [],
                "avatars": [],
                "total_users": 0
            }
        
        with open("main.json", 'r') as f:
            data = json.load(f)
        
        # Initialize counters
        saved_item_counts = {}
        avatar_counts = {}
        total_users = len(data)
        
        # Count saved items and avatars
        for user_id, user_data in data.items():
            # Count saved items
            if "saved" in user_data:
                saved_items = user_data["saved"]
                
                # Handle different data types
                if isinstance(saved_items, list):
                    for item in saved_items:
                        item_str = str(item)
                        saved_item_counts[item_str] = saved_item_counts.get(item_str, 0) + 1
                elif isinstance(saved_items, (str, int)):
                    item_str = str(saved_items)
                    saved_item_counts[item_str] = saved_item_counts.get(item_str, 0) + 1
            
            # Count avatars
            if "avatar" in user_data:
                avatar_id = str(user_data["avatar"])
                avatar_counts[avatar_id] = avatar_counts.get(avatar_id, 0) + 1
        
        # Sort by popularity (descending)
        sorted_saved_items = sorted(
            saved_item_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        sorted_avatars = sorted(
            avatar_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Format results
        saved_items_stats = [
            {
                "id": item_id,
                "count": count,
                "percentage": round((count / total_users) * 100, 1) if total_users > 0 else 0
            }
            for item_id, count in sorted_saved_items
        ]
        
        avatars_stats = [
            {
                "avatar_id": avatar_id,
                "count": count,
                "percentage": round((count / total_users) * 100, 1) if total_users > 0 else 0
            }
            for avatar_id, count in sorted_avatars[:3]  # Limit to top 3
        ]
        
        return {
            "saved_items": saved_items_stats,
            "avatars": avatars_stats,
            "total_users": total_users
        }
        
    except Exception as e:
        raise ValueError(f"Error generating stats: {str(e)}")
