import copy
from typing import Any

class DeepCopyError(Exception):
    pass


def safe_deepcopy(obj: Any) -> Any:
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    elif isinstance(obj, list):
        return [safe_deepcopy(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: safe_deepcopy(value) for key, value in obj.items()}
    elif isinstance(obj, tuple):
        return tuple(safe_deepcopy(item) for item in obj)
    elif isinstance(obj, set):
        return {safe_deepcopy(item) for item in obj}
    else:
        try:
            return copy.copy(obj)
        except TypeError:
            return obj
        except Exception:
            return obj
