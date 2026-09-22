"""أدوات مساعدة للتعامل مع JSON و numpy"""
import numpy as np
import json


def to_python_type(obj):
    """تحويل أي قيمة numpy إلى Python native لـ JSON"""
    if isinstance(obj, dict):
        return {k: to_python_type(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [to_python_type(v) for v in obj]
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    return obj


def save_json(data, filepath):
    """حفظ JSON بأمان مع تحويل قيم numpy"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(to_python_type(data), f, ensure_ascii=False, indent=2)