"""
Utilidades para convertir entre tipos Python nativos y tipos DynamoDB.

DynamoDB no acepta float — usa Decimal. Este módulo centraliza la conversión.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime


def to_dynamo(obj):
    """Convierte recursivamente floats → Decimal y datetimes → str ISO."""
    if isinstance(obj, bool):
        return obj  # bool antes que int (bool es subclase de int)
    if isinstance(obj, float):
        return Decimal(str(round(obj, 10)))
    if isinstance(obj, int):
        return obj
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: to_dynamo(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, (list, tuple)):
        return [to_dynamo(i) for i in obj]
    return obj


def from_dynamo(obj):
    """Convierte recursivamente Decimal → float/int."""
    if isinstance(obj, Decimal):
        f = float(obj)
        return int(f) if f == int(f) else f
    if isinstance(obj, dict):
        return {k: from_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [from_dynamo(i) for i in obj]
    return obj
