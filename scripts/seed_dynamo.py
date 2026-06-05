#!/usr/bin/env python3
"""
seed_dynamo.py — Poblar DynamoDB Local con datos de prueba realistas.

Uso:
    python ms-ai/scripts/seed_dynamo.py

Requisitos: pip install boto3
DynamoDB Local debe estar corriendo en localhost:8001
"""
import random
import time
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import os

import boto3
from boto3.dynamodb.conditions import Key

# ── Conexión ──────────────────────────────────────────────────────────────────
# Dentro del contenedor: http://dynamodb-local:8000
# Fuera (host local):    http://localhost:8001
ENDPOINT = os.getenv("DYNAMODB_ENDPOINT_URL", "http://localhost:8001")
REGION   = os.getenv("AWS_REGION", "us-east-1")

dynamodb = boto3.resource(
    "dynamodb",
    endpoint_url=ENDPOINT,
    region_name=REGION,
    aws_access_key_id="local",
    aws_secret_access_key="local",
)
client = boto3.client(
    "dynamodb",
    endpoint_url=ENDPOINT,
    region_name=REGION,
    aws_access_key_id="local",
    aws_secret_access_key="local",
)


# ── Helpers ───────────────────────────────────────────────────────────────────
def D(x: float) -> Decimal:
    return Decimal(str(round(x, 6)))


def iso(dt: datetime) -> str:
    return dt.isoformat()


def ensure_tables():
    existing = client.list_tables()["TableNames"]
    TABLES = [
        {
            "TableName": "edupay-predictions",
            "KeySchema": [
                {"AttributeName": "familyId",      "KeyType": "HASH"},
                {"AttributeName": "predictionDate", "KeyType": "RANGE"},
            ],
            "AttributeDefinitions": [
                {"AttributeName": "familyId",      "AttributeType": "S"},
                {"AttributeName": "predictionDate", "AttributeType": "S"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
        },
        {
            "TableName": "edupay-clusters",
            "KeySchema": [{"AttributeName": "familyId", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "familyId", "AttributeType": "S"}],
            "BillingMode": "PAY_PER_REQUEST",
        },
        {
            "TableName": "edupay-ocr",
            "KeySchema": [
                {"AttributeName": "familyId",  "KeyType": "HASH"},
                {"AttributeName": "createdAt", "KeyType": "RANGE"},
            ],
            "AttributeDefinitions": [
                {"AttributeName": "familyId",  "AttributeType": "S"},
                {"AttributeName": "createdAt", "AttributeType": "S"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
        },
        {
            "TableName": "edupay-payment-events",
            "KeySchema": [
                {"AttributeName": "familyId", "KeyType": "HASH"},
                {"AttributeName": "sk",       "KeyType": "RANGE"},
            ],
            "AttributeDefinitions": [
                {"AttributeName": "familyId", "AttributeType": "S"},
                {"AttributeName": "sk",       "AttributeType": "S"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
        },
        {
            "TableName": "edupay-model-registry",
            "KeySchema": [
                {"AttributeName": "modelName", "KeyType": "HASH"},
                {"AttributeName": "version",   "KeyType": "RANGE"},
            ],
            "AttributeDefinitions": [
                {"AttributeName": "modelName", "AttributeType": "S"},
                {"AttributeName": "version",   "AttributeType": "S"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
        },
        {
            "TableName": "edupay-documents",
            "KeySchema": [{"AttributeName": "docId", "KeyType": "HASH"}],
            "AttributeDefinitions": [
                {"AttributeName": "docId",      "AttributeType": "S"},
                {"AttributeName": "familyId",   "AttributeType": "S"},
                {"AttributeName": "uploadedAt", "AttributeType": "S"},
            ],
            "GlobalSecondaryIndexes": [{
                "IndexName": "familyId-uploadedAt-index",
                "KeySchema": [
                    {"AttributeName": "familyId",   "KeyType": "HASH"},
                    {"AttributeName": "uploadedAt", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }],
            "BillingMode": "PAY_PER_REQUEST",
        },
    ]
    for t in TABLES:
        if t["TableName"] not in existing:
            client.create_table(**t)
            print(f"  [create] {t['TableName']}")
        else:
            print(f"  [skip]   {t['TableName']} ya existe")


# ── Datos maestros ─────────────────────────────────────────────────────────────
TUTOR_NAMES = [
    "Juan Carlos Perez",  "Maria Elena Lopez",  "Roberto Gutierrez",
    "Ana Lucia Flores",   "Carlos Mendoza",     "Patricia Vargas",
    "Luis Alberto Rojas", "Carmen Rosa Quispe", "Fernando Mamani",
    "Silvia Condori",     "Marcos Antonio Rios","Elena Beatriz Cruz",
    "Diego Herrera",      "Rosa Maria Arce",    "Jorge Pinto",
    "Claudia Vega",       "Alejandro Soria",    "Monica Bustamante",
    "Hector Villanueva",  "Gabriela Miranda",
]
CLUSTER_LABELS  = ["PUNTUAL_ESTRELLA", "REGULAR", "IRREGULAR", "MOROSO_CRONICO"]
CLUSTER_ACTIONS = {
    "PUNTUAL_ESTRELLA": "Ofrecer beneficios por fidelidad y descuentos anticipados.",
    "REGULAR":          "Enviar recordatorios preventivos 5 días antes del vencimiento.",
    "IRREGULAR":        "Contactar personalmente y ofrecer plan de pagos flexibles.",
    "MOROSO_CRONICO":   "Iniciar proceso de cobranza formal y suspensión de servicios.",
}
METHODS   = ["QR", "STRIPE", "BLOCKCHAIN"]
RISK_DIST = {
    "PUNTUAL_ESTRELLA": ("LOW",    0.05, 0.25),
    "REGULAR":          ("MEDIUM", 0.30, 0.55),
    "IRREGULAR":        ("MEDIUM", 0.50, 0.70),
    "MOROSO_CRONICO":   ("HIGH",   0.72, 0.97),
}
BANKS = ["BNB", "Banco Unión", "BISA", "FIE", "Prodem", "Banco Sol"]
DOC_TYPES  = ["CI_TUTOR", "CI_ALUMNO", "CERT_NACIMIENTO", "CONTRATO", "COMPROBANTE"]
DOC_STATUS = ["PENDING", "APPROVED", "REJECTED"]


# ── Seed ─────────────────────────────────────────────────────────────────────

def seed_model_registry():
    tbl = dynamodb.Table("edupay-model-registry")
    models = [
        {
            "modelName":       "mora_predictor",
            "version":         "lgbm-v1.0.0",
            "algorithm":       "LightGBM",
            "trainedAt":       iso(datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)),
            "trainingSamples": 12500,
            "metrics":         {"auc": D(0.883), "f1": D(0.791), "accuracy": D(0.847)},
            "featuresUsed":    ["avg_days_late_last_3_months", "months_paid_on_time_ratio",
                                "consecutive_late_payments", "uses_mobile_app"],
            "artifactS3Key":   "models/mora_predictor/lgbm-v1.0.0/model.pkl",
            "isProduction":    True,
        },
        {
            "modelName":       "family_clusterer",
            "version":         "kmeans-v1.0.0",
            "algorithm":       "KMeans",
            "trainedAt":       iso(datetime(2026, 1, 20, 14, 30, 0, tzinfo=timezone.utc)),
            "trainingSamples": 8200,
            "metrics":         {"silhouetteScore": D(0.652), "inertia": D(1843.7)},
            "featuresUsed":    ["avg_payment_day", "mora_incidence", "method_consistency",
                                "months_active"],
            "artifactS3Key":   "models/family_clusterer/kmeans-v1.0.0/model.pkl",
            "isProduction":    True,
        },
    ]
    for m in models:
        tbl.put_item(Item=m)
    print(f"  [model-registry] {len(models)} modelos registrados")


def seed_clusters(families: list[dict]) -> None:
    tbl = dynamodb.Table("edupay-clusters")
    for fam in families:
        label  = fam["cluster_label"]
        action = CLUSTER_ACTIONS[label]
        fam_id = fam["familyId"]
        mora   = {"PUNTUAL_ESTRELLA": 0.04, "REGULAR": 0.22, "IRREGULAR": 0.51, "MOROSO_CRONICO": 0.87}[label]
        item = {
            "familyId":          fam_id,
            "cluster":           CLUSTER_LABELS.index(label),
            "clusterLabel":      label,
            "modelVersion":      "kmeans-v1.0.0",
            "recommendedAction": action,
            "computedAt":        iso(datetime.now(timezone.utc)),
            "features": {
                "avg_payment_day":       D(random.uniform(5, 25)),
                "std_dev_payment_day":   D(random.uniform(0.5, 5)),
                "mora_incidence":        D(mora + random.uniform(-0.05, 0.05)),
                "annual_payer_score":    D(random.uniform(0, 1)),
                "method_consistency":   D(random.uniform(0.4, 1)),
                "months_active":        random.randint(6, 36),
            },
        }
        tbl.put_item(Item=item)
    print(f"  [clusters] {len(families)} familias clusterizadas")


def seed_predictions(families: list[dict]) -> int:
    tbl    = dynamodb.Table("edupay-predictions")
    total  = 0
    now    = datetime.now(timezone.utc)

    for fam in families:
        label    = fam["cluster_label"]
        level, lo, hi = RISK_DIST[label]
        n_preds  = random.randint(4, 8)

        for i in range(n_preds):
            pred_date = now - timedelta(days=i * 30 + random.randint(0, 15))
            score     = round(random.uniform(lo, hi), 4)
            # Ajuste: score muy alto → HIGH, bajo → LOW
            if score >= 0.70:
                rl = "HIGH"
            elif score >= 0.40:
                rl = "MEDIUM"
            else:
                rl = "LOW"

            epoch = int(pred_date.timestamp() * 1000)
            sk    = f"{pred_date.strftime('%Y-%m-%d')}#{epoch}"

            item = {
                "familyId":       fam["familyId"],
                "predictionDate": sk,
                "riskScore":      D(score),
                "riskLevel":      rl,
                "modelVersion":   "lgbm-v1.0.0",
                "predictionDatePlain": pred_date.strftime("%Y-%m-%d"),
                "features": {
                    "avg_days_late_last_3_months":          D(random.uniform(0, 15)),
                    "max_days_late_ever":                   D(random.uniform(0, 60)),
                    "months_paid_on_time_ratio":            D(random.uniform(0.3, 1)),
                    "consecutive_late_payments":            random.randint(0, 6),
                    "has_paid_annual_ever":                 random.choice([True, False]),
                    "preferred_payment_method_qr":         random.choice([True, False]),
                    "preferred_payment_method_stripe":     random.choice([True, False]),
                    "preferred_payment_method_blockchain": random.choice([True, False]),
                    "avg_payment_day_of_month":            D(random.uniform(5, 25)),
                    "uses_mobile_app":                     random.choice([True, False]),
                    "num_students":                        random.randint(1, 4),
                    "years_enrolled":                      random.randint(1, 8),
                    "has_discount":                        random.choice([True, False]),
                    "month":                               pred_date.month,
                    "is_after_carnaval":                   pred_date.month in [3, 4],
                    "months_remaining_year":               12 - pred_date.month,
                },
                "actualOutcome": None,
                "createdAt":     iso(pred_date),
            }
            tbl.put_item(Item=item)
            total += 1

    print(f"  [predictions] {total} predicciones creadas")
    return total


def seed_payment_events(families: list[dict]) -> int:
    tbl   = dynamodb.Table("edupay-payment-events")
    total = 0
    now   = datetime.now(timezone.utc)

    for fam in families:
        label   = fam["cluster_label"]
        n_months = 18  # últimos 18 meses
        base_amount = random.choice([750, 850, 920, 1050, 1200, 1350, 1500])

        for m in range(n_months):
            month_date = now - timedelta(days=m * 30)
            month      = month_date.month
            year       = month_date.year
            due_date   = month_date.replace(day=10)

            # Familias morosas a veces no pagan
            if label == "MOROSO_CRONICO" and random.random() < 0.35:
                continue
            if label == "IRREGULAR" and random.random() < 0.15:
                continue

            days_late = {
                "PUNTUAL_ESTRELLA": random.randint(-5, 2),
                "REGULAR":          random.randint(-2, 8),
                "IRREGULAR":        random.randint(0, 20),
                "MOROSO_CRONICO":   random.randint(10, 45),
            }[label]

            paid_at    = due_date + timedelta(days=max(days_late, 0))
            payment_id = f"PAY-{fam['familyId']}-{year}{month:02d}"
            method     = random.choices(METHODS, weights=[50, 35, 15])[0]
            amount     = base_amount + random.randint(-50, 100)
            event_type = "payment.failed" if days_late > 30 else "payment.confirmed"
            sk         = f"{iso(paid_at)}#{payment_id}"

            item = {
                "familyId":   fam["familyId"],
                "sk":         sk,
                "paymentId":  payment_id,
                "studentId":  fam["familyId"].replace("FAM", "STU"),
                "eventType":  event_type,
                "month":      month,
                "year":       year,
                "method":     method,
                "amountBOB":  D(float(amount)),
                "paidAt":     iso(paid_at),
                "dueDate":    iso(due_date),
                "daysLate":   days_late,
                "createdAt":  iso(paid_at),
            }
            tbl.put_item(Item=item)
            total += 1

    print(f"  [payment-events] {total} eventos de pago creados")
    return total


def seed_ocr(families: list[dict]) -> int:
    tbl   = dynamodb.Table("edupay-ocr")
    total = 0
    now   = datetime.now(timezone.utc)

    for fam in families:
        n_analyses = random.randint(1, 5)
        for i in range(n_analyses):
            created_at = now - timedelta(days=random.randint(1, 180))
            bank       = random.choice(BANKS)
            amount     = round(random.uniform(500, 1600), 2)

            item = {
                "familyId":   fam["familyId"],
                "createdAt":  iso(created_at),
                "userId":     fam["familyId"].replace("FAM", "USR"),
                "imageS3Key": f"ocr-uploads/{created_at.year}/{created_at.month:02d}/receipt_{uuid.uuid4().hex[:8]}.jpg",
                "confidence": D(round(random.uniform(0.70, 0.99), 4)),
                "extracted": {
                    "bank":      bank,
                    "amount":    D(amount),
                    "currency":  "BOB",
                    "date":      created_at.strftime("%Y-%m-%d"),
                    "time":      created_at.strftime("%H:%M"),
                    "reference": f"REF-{uuid.uuid4().hex[:10].upper()}",
                    "concept":   "PAGO MENSUALIDAD ESCOLAR",
                },
                "rawOcrText":        f"BANCO {bank.upper()} TRANSFERENCIA BOB {amount:.2f}",
                "wasAcceptedByUser": random.choice([True, True, False]),
                "correctionsByUser": {},
                "modelVersion":      "pillow-ocr-v1.0",
                "processingTimeMs":  random.randint(120, 850),
            }
            tbl.put_item(Item=item)
            total += 1

    print(f"  [ocr] {total} análisis OCR creados")
    return total


def seed_documents(families: list[dict]) -> int:
    tbl   = dynamodb.Table("edupay-documents")
    total = 0
    now   = datetime.now(timezone.utc)

    for fam in families:
        n_docs = random.randint(2, 5)
        for i in range(n_docs):
            uploaded_at = now - timedelta(days=random.randint(1, 90))
            doc_type    = random.choice(DOC_TYPES)
            status_w    = [0.4, 0.45, 0.15]   # PENDING, APPROVED, REJECTED
            status      = random.choices(DOC_STATUS, weights=status_w)[0]
            doc_id      = str(uuid.uuid4())

            item = {
                "docId":           doc_id,
                "familyId":        fam["familyId"],
                "studentId":       None,
                "type":            doc_type,
                "originalName":    f"{doc_type.lower()}_{fam['familyId']}.pdf",
                "s3Key":           f"families/{fam['familyId']}/{doc_type.lower()}/{uploaded_at.strftime('%Y%m%d%H%M%S')}.pdf",
                "s3Bucket":        "edupay-scz-docs",
                "mimeType":        "application/pdf",
                "sizeBytes":       random.randint(50_000, 2_000_000),
                "status":          status,
                "rejectionReason": "Documento ilegible" if status == "REJECTED" else None,
                "uploadedBy":      fam["familyId"].lower().replace("fam-", "tutor"),
                "reviewedBy":      "admin@edupay.bo" if status != "PENDING" else None,
                "reviewedAt":      iso(uploaded_at + timedelta(days=random.randint(1, 5))) if status != "PENDING" else None,
                "uploadedAt":      iso(uploaded_at),
                "aiValidation":    None,
            }
            # Limpiar Nones
            item = {k: v for k, v in item.items() if v is not None}
            tbl.put_item(Item=item)
            total += 1

    print(f"  [documents] {total} documentos creados")
    return total


def build_families() -> list[dict]:
    families = []
    # Asignar clusters de forma realista: 30% estrella, 35% regular, 25% irregular, 10% moroso
    weights = [30, 35, 25, 10]
    for i, name in enumerate(TUTOR_NAMES, start=1):
        fam_id = f"FAM-{i:03d}"
        label  = random.choices(CLUSTER_LABELS, weights=weights)[0]
        families.append({
            "familyId":     fam_id,
            "tutorName":    name,
            "cluster_label": label,
        })
    return families


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🌱 EduPay — Seed DynamoDB Local")
    print("=" * 50)

    print("\n📦 Verificando/creando tablas...")
    ensure_tables()

    print("\n🤖 Registrando modelos ML...")
    seed_model_registry()

    print("\n👨‍👩‍👧 Generando familias...")
    families = build_families()
    print(f"  {len(families)} familias: {[f['familyId'] for f in families[:5]]}...")

    print("\n🎯 Seeding clusters...")
    seed_clusters(families)

    print("\n📊 Seeding predicciones de riesgo...")
    seed_predictions(families)

    print("\n💳 Seeding eventos de pago...")
    seed_payment_events(families)

    print("\n🔍 Seeding análisis OCR...")
    seed_ocr(families)

    print("\n📄 Seeding documentos...")
    seed_documents(families)

    print("\n✅ Seed completado!")
    print("   Tablas pobladas:")

    for t in ["edupay-predictions", "edupay-clusters", "edupay-ocr",
              "edupay-payment-events", "edupay-model-registry", "edupay-documents"]:
        table = dynamodb.Table(t)
        count = table.scan(Select="COUNT")["Count"]
        print(f"   • {t:<30} → {count:>4} ítems")
