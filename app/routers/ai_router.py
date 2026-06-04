from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.database import get_db
from app.ml.supervised.mora_predictor import MoraPredictor
from app.ml.unsupervised.family_clusterer import FamilyClusterer
from app.ml.ocr.receipt_analyzer import ReceiptAnalyzer
from app.models.prediction import PredictionFeatures, RiskScoreResponse
from app.models.cluster import ClusterFeatures, ClusterResponse
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.cluster_repository import ClusterRepository
from app.repositories.ocr_repository import OcrRepository

router = APIRouter(prefix="/ai", tags=["AI"])


# ── Risk Score ─────────────────────────────────────────────────────────────────

@router.post("/family/{family_id}/risk-score", response_model=RiskScoreResponse)
async def get_risk_score(family_id: str, features: PredictionFeatures):
    predictor = MoraPredictor.get()
    feature_dict = {
        **features.model_dump(),
        "has_paid_annual_ever": int(features.has_paid_annual_ever),
        "preferred_payment_method_qr": int(features.preferred_payment_method_qr),
        "preferred_payment_method_stripe": int(features.preferred_payment_method_stripe),
        "preferred_payment_method_blockchain": int(features.preferred_payment_method_blockchain),
        "uses_mobile_app": int(features.uses_mobile_app),
        "has_discount": int(features.has_discount),
        "is_after_carnaval": int(features.is_after_carnaval),
    }

    result = predictor.predict(feature_dict)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    doc = {
        "familyId": family_id,
        "predictionDate": today,
        "riskScore": result["riskScore"],
        "riskLevel": result["riskLevel"],
        "modelVersion": predictor.version,
        "features": feature_dict,
        "actualOutcome": None,
        "createdAt": datetime.now(timezone.utc),
    }

    await PredictionRepository(get_db()).save(doc)

    return RiskScoreResponse(
        familyId=family_id,
        riskScore=result["riskScore"],
        riskLevel=result["riskLevel"],
        modelVersion=predictor.version,
        features=feature_dict,
        predictionDate=today,
    )


@router.get("/family/{family_id}/risk-score/history")
async def get_risk_history(family_id: str):
    history = await PredictionRepository(get_db()).find_by_family(family_id)
    if not history:
        raise HTTPException(status_code=404, detail="No predictions found for this family")
    return {"familyId": family_id, "predictions": history}


# ── Cluster ────────────────────────────────────────────────────────────────────

@router.post("/family/{family_id}/cluster", response_model=ClusterResponse)
async def assign_cluster(family_id: str, features: ClusterFeatures):
    clusterer = FamilyClusterer.get()
    feature_dict = features.model_dump()
    result = clusterer.predict(feature_dict)
    now = datetime.now(timezone.utc)

    doc = {
        "familyId": family_id,
        "cluster": result["cluster"],
        "clusterLabel": result["clusterLabel"],
        "modelVersion": clusterer.version,
        "features": feature_dict,
        "recommendedAction": result["recommendedAction"],
        "computedAt": now,
    }

    await ClusterRepository(get_db()).upsert(family_id, doc)

    return ClusterResponse(
        familyId=family_id,
        cluster=result["cluster"],
        clusterLabel=result["clusterLabel"],
        recommendedAction=result["recommendedAction"],
        modelVersion=clusterer.version,
        features=feature_dict,
        computedAt=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


@router.get("/family/{family_id}/cluster")
async def get_cluster(family_id: str):
    doc = await ClusterRepository(get_db()).find_by_family(family_id)
    if not doc:
        raise HTTPException(status_code=404, detail="No cluster found for this family")
    return doc


# ── OCR ────────────────────────────────────────────────────────────────────────

@router.post("/receipt/analyze")
async def analyze_receipt(
    file: UploadFile = File(...),
    family_id: str = Form(...),
    user_id: str = Form(...),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_bytes = await file.read()
    analyzer = ReceiptAnalyzer.get()
    result = analyzer.analyze(image_bytes)
    now = datetime.now(timezone.utc)

    doc = {
        "userId": user_id,
        "familyId": family_id,
        "imageS3Key": f"ocr-uploads/{now.year}/{now.month:02d}/{file.filename}",
        "confidence": result.confidence,
        "extracted": {
            "bank": result.bank,
            "amount": result.amount,
            "currency": result.currency,
            "date": result.date,
            "time": result.time,
            "reference": result.reference,
            "concept": result.concept,
        },
        "rawOcrText": result.raw_text,
        "wasAcceptedByUser": False,
        "correctionsByUser": {},
        "modelVersion": result.model_version,
        "processingTimeMs": result.processing_time_ms,
        "createdAt": now,
    }

    await OcrRepository(get_db()).save(doc)

    return {
        "familyId": family_id,
        "confidence": result.confidence,
        "extracted": doc["extracted"],
        "processingTimeMs": result.processing_time_ms,
        "modelVersion": result.model_version,
    }


@router.get("/receipt/history/{family_id}")
async def get_ocr_history(family_id: str):
    docs = await OcrRepository(get_db()).find_by_family(family_id)
    if not docs:
        raise HTTPException(status_code=404, detail="No OCR analyses found for this family")
    return {"familyId": family_id, "analyses": docs}
