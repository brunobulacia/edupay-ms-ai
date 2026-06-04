"""
Handlers de mensajes RabbitMQ.

Cada handler recibe el *payload* del mensaje (dict ya parseado) y retorna
un dict con la respuesta que se publicará de vuelta al API Gateway.

Reutilizan la lógica de negocio existente directamente, sin duplicar código.
"""
import logging
from datetime import datetime, timezone

from app.database import get_db
from app.ml.supervised.mora_predictor import MoraPredictor
from app.ml.unsupervised.family_clusterer import FamilyClusterer
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.cluster_repository import ClusterRepository
from app.repositories.payment_event_repository import PaymentEventRepository

logger = logging.getLogger(__name__)


# ── Risk Score ─────────────────────────────────────────────────────────────────

async def handle_risk_score(payload: dict) -> dict:
    """
    Mensaje esperado:
    {
        "familyId": "abc123",
        "features": { ...PredictionFeatures fields... }
    }
    """
    family_id = payload["familyId"]
    features = payload["features"]

    predictor = MoraPredictor.get()
    feature_dict = {
        **features,
        "has_paid_annual_ever":               int(features.get("has_paid_annual_ever", 0)),
        "preferred_payment_method_qr":        int(features.get("preferred_payment_method_qr", 0)),
        "preferred_payment_method_stripe":    int(features.get("preferred_payment_method_stripe", 0)),
        "preferred_payment_method_blockchain":int(features.get("preferred_payment_method_blockchain", 0)),
        "uses_mobile_app":                    int(features.get("uses_mobile_app", 0)),
        "has_discount":                       int(features.get("has_discount", 0)),
        "is_after_carnaval":                  int(features.get("is_after_carnaval", 0)),
    }

    result = predictor.predict(feature_dict)
    today  = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    doc = {
        "familyId":       family_id,
        "predictionDate": today,
        "riskScore":      result["riskScore"],
        "riskLevel":      result["riskLevel"],
        "modelVersion":   predictor.version,
        "features":       feature_dict,
        "actualOutcome":  None,
        "createdAt":      datetime.now(timezone.utc),
    }
    await PredictionRepository(get_db()).save(doc)

    return {
        "familyId":     family_id,
        "riskScore":    result["riskScore"],
        "riskLevel":    result["riskLevel"],
        "modelVersion": predictor.version,
        "predictionDate": today,
    }


# ── Cluster ────────────────────────────────────────────────────────────────────

async def handle_cluster(payload: dict) -> dict:
    """
    Mensaje esperado:
    {
        "familyId": "abc123",
        "features": { ...ClusterFeatures fields... }
    }
    """
    family_id = payload["familyId"]
    features  = payload["features"]

    clusterer = FamilyClusterer.get()
    result    = clusterer.predict(features)
    now       = datetime.now(timezone.utc)

    doc = {
        "familyId":          family_id,
        "cluster":           result["cluster"],
        "clusterLabel":      result["clusterLabel"],
        "modelVersion":      clusterer.version,
        "features":          features,
        "recommendedAction": result["recommendedAction"],
        "computedAt":        now,
    }
    await ClusterRepository(get_db()).upsert(family_id, doc)

    return {
        "familyId":          family_id,
        "cluster":           result["cluster"],
        "clusterLabel":      result["clusterLabel"],
        "recommendedAction": result["recommendedAction"],
        "modelVersion":      clusterer.version,
        "computedAt":        now.isoformat(),
    }


# ── Payment Event ──────────────────────────────────────────────────────────────

async def handle_payment_event(payload: dict) -> dict:
    """
    Mensaje esperado: campos del modelo PaymentEventIn como dict plano.
    """
    doc = {
        **payload,
        "createdAt": datetime.now(timezone.utc),
    }
    await PaymentEventRepository(get_db()).save(doc)

    return {
        "status":    "received",
        "familyId":  payload.get("familyId"),
        "paymentId": payload.get("paymentId"),
    }
