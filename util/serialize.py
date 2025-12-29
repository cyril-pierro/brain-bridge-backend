from datetime import date
from uuid import UUID


def serialize_data(data):
    """Convert datetime, enum, and UUID objects to serializable formats for caching."""
    if isinstance(data, dict):
        return {k: serialize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_data(item) for item in data]
    elif isinstance(data, date):
        return data.isoformat()
    elif isinstance(data, UUID):
        return str(data)
    elif hasattr(data, 'value'):  # Enum
        return data.value
    else:
        return data
