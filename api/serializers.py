"""Serialization utilities for MongoDB BSON types (ObjectId, datetime)."""
from datetime import date, datetime
from bson import ObjectId


def serialize_doc(doc):
    """Recursively convert MongoDB document BSON types into JSON-serializable Python types."""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        clean = {}
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                clean[k] = str(v)
            elif isinstance(v, (datetime, date)):
                clean[k] = v.isoformat()
            elif isinstance(v, (dict, list)):
                clean[k] = serialize_doc(v)
            else:
                clean[k] = v
        return clean
    if isinstance(doc, ObjectId):
        return str(doc)
    if isinstance(doc, (datetime, date)):
        return doc.isoformat()
    return doc
