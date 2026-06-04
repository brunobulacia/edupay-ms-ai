# MS-IA — Guía de trabajo
## Colecciones MongoDB, modelos de ML y datasets

> Este documento describe cómo estructurar las colecciones de MongoDB del microservicio de inteligencia artificial, cómo abordar cada uno de los tres modelos (Deep Learning, ML Supervisado, ML No Supervisado) y de dónde obtener los datasets necesarios para entrenar cada uno.

---

## 1. Contexto del microservicio

El **MS-IA** tiene tres responsabilidades principales:

1. **Deep Learning — OCR de comprobantes bancarios bolivianos**
   Recibe la foto de un recibo bancario y extrae automáticamente los datos (banco, monto, fecha, referencia).

2. **ML Supervisado — Predicción de mora**
   Calcula la probabilidad de que cada familia se atrase en el pago del próximo mes.

3. **ML No Supervisado — Segmentación de familias**
   Agrupa a las familias en 4 clusters según su comportamiento histórico de pago.

Adicionalmente, gestiona la subida y descarga de documentos en S3 y mantiene un registro de las predicciones y eventos en MongoDB (después se migrará a DynamoDB).

---

## 2. Colecciones de MongoDB

Cada modelo y proceso necesita su propia colección. Diseñá los documentos pensando en cómo se verán mañana en DynamoDB, así la migración será directa.

### 2.1. Colección `predictions`

Almacena las predicciones de mora generadas por el modelo supervisado, una por familia por fecha.

```javascript
// predictions
{
  "_id": ObjectId("..."),
  "familyId": "uuid-de-la-familia",         // viene del MS-Gestión (PostgreSQL)
  "predictionDate": "2025-10-01",            // fecha en la que se generó (YYYY-MM-DD)
  "riskScore": 0.73,                         // 0.0 a 1.0
  "riskLevel": "HIGH",                       // LOW | MEDIUM | HIGH
  "modelVersion": "lgbm-v1.2.0",
  "features": {                              // snapshot de las variables usadas
    "avgDaysLateLast3Months": 5.2,
    "maxDaysLateEver": 18,
    "monthsPaidOnTimeRatio": 0.65,
    "consecutiveLatePayments": 2,
    "hasPaidAnnualEver": false,
    "preferredPaymentMethod": "QR",
    "numStudents": 2,
    "yearsEnrolled": 3,
    "month": 10
  },
  "actualOutcome": null,                     // se rellena cuando termina el mes
  "createdAt": ISODate("2025-10-01T08:00:00Z")
}

// Índices recomendados:
db.predictions.createIndex({ familyId: 1, predictionDate: -1 });
db.predictions.createIndex({ riskLevel: 1, predictionDate: -1 });
```

### 2.2. Colección `clusters`

Almacena el cluster asignado a cada familia. Se recalcula mensualmente.

```javascript
// clusters
{
  "_id": ObjectId("..."),
  "familyId": "uuid-de-la-familia",
  "cluster": 2,                              // 0, 1, 2, 3
  "clusterLabel": "IRREGULAR",               // PUNTUAL_ESTRELLA | REGULAR | IRREGULAR | MOROSO_CRONICO
  "modelVersion": "kmeans-v1.0.0",
  "features": {
    "avgPaymentDay": 12.4,                   // día promedio del mes en que paga
    "stdDevPaymentDay": 4.1,                 // dispersión
    "moraIncidence": 0.35,                   // % de meses con mora
    "annualPayerScore": 0.0                  // ha pagado anual?
  },
  "recommendedAction": "Recordatorio proactivo día 3",
  "computedAt": ISODate("2025-10-01T02:00:00Z")
}

// Índices:
db.clusters.createIndex({ familyId: 1 });
db.clusters.createIndex({ clusterLabel: 1 });
```

### 2.3. Colección `ocr_analyses`

Cada vez que un padre fotografía un comprobante, queda registrado el análisis OCR para auditoría y reentrenamiento.

```javascript
// ocr_analyses
{
  "_id": ObjectId("..."),
  "userId": "uuid-del-padre",
  "familyId": "uuid-de-la-familia",
  "imageS3Key": "ocr-uploads/2025/10/abc123.jpg",  // referencia a la imagen original
  "confidence": 0.94,
  "extracted": {
    "bank": "Banco Nacional de Bolivia",
    "amount": 850.00,
    "currency": "BOB",
    "date": "2025-10-07",
    "time": "14:23:11",
    "reference": "0042891234",
    "concept": "MENSUALIDAD OCTUBRE"
  },
  "rawOcrText": "BNB COMPROBANTE DE PAGO BS. 850.00...",
  "wasAcceptedByUser": true,                 // el padre confirmó los datos?
  "correctionsByUser": {},                   // qué corrigió manualmente
  "modelVersion": "trocr-bolivia-v1",
  "processingTimeMs": 1243,
  "createdAt": ISODate("2025-10-07T14:25:00Z")
}

// Índices:
db.ocr_analyses.createIndex({ familyId: 1, createdAt: -1 });
db.ocr_analyses.createIndex({ wasAcceptedByUser: 1 });   // para reentrenamiento
```

### 2.4. Colección `payment_events`

Registro de eventos que llegan desde MS-Pagos vía EventBridge. Sirve como histórico para alimentar a los modelos de ML.

```javascript
// payment_events
{
  "_id": ObjectId("..."),
  "familyId": "uuid-de-la-familia",
  "studentId": "uuid-del-alumno",
  "paymentId": "uuid-del-pago",
  "eventType": "payment.confirmed",          // confirmed | failed | refunded
  "month": 10,
  "year": 2025,
  "method": "STRIPE",                        // QR | STRIPE | BLOCKCHAIN
  "amountBOB": 850.00,
  "paidAt": ISODate("2025-10-07T14:23:00Z"),
  "dueDate": ISODate("2025-10-10T23:59:59Z"),
  "daysLate": -3,                            // negativo = antes del vencimiento
  "createdAt": ISODate("2025-10-07T14:23:30Z")
}

// Índices:
db.payment_events.createIndex({ familyId: 1, year: 1, month: 1 });
db.payment_events.createIndex({ paidAt: -1 });
```

### 2.5. Colección `model_registry`

Lleva el control de qué modelos están en producción, cuándo fueron entrenados y cuál es su métrica de calidad.

```javascript
// model_registry
{
  "_id": ObjectId("..."),
  "modelName": "mora_predictor",             // mora_predictor | family_clusterer | receipt_ocr
  "version": "v1.2.0",
  "algorithm": "LightGBM",
  "trainedAt": ISODate("2025-10-01T00:00:00Z"),
  "trainingSamples": 4500,
  "metrics": {
    "aucRoc": 0.89,
    "precision": 0.75,
    "recall": 0.71,
    "f1": 0.73
  },
  "artifactS3Key": "models/mora_predictor/v1.2.0/model.pkl",
  "featuresUsed": ["avgDaysLateLast3Months", "maxDaysLateEver", "..."],
  "isProduction": true,
  "createdAt": ISODate("2025-10-01T01:00:00Z")
}

// Índices:
db.model_registry.createIndex({ modelName: 1, isProduction: 1 });
```

### 2.6. Colección `documents`

Metadatos de cada documento que el padre o admin sube. El archivo en sí vive en S3.

```javascript
// documents
{
  "_id": ObjectId("..."),
  "familyId": "uuid-de-la-familia",
  "studentId": "uuid-del-alumno",            // opcional
  "type": "CI_ALUMNO",                       // CI_ALUMNO | CI_TUTOR | CERT_NACIMIENTO | CONTRATO | etc.
  "originalName": "ci_juan_perez.pdf",
  "s3Key": "families/uuid/students/uuid/ci_20251007.pdf",
  "s3Bucket": "edupay-scz-docs",
  "mimeType": "application/pdf",
  "sizeBytes": 245678,
  "status": "PENDING",                       // PENDING | APPROVED | REJECTED | ARCHIVED
  "rejectionReason": null,
  "uploadedBy": "uuid-del-usuario",
  "reviewedBy": null,
  "reviewedAt": null,
  "uploadedAt": ISODate("2025-10-07T14:00:00Z"),
  "aiValidation": {                          // si se validó con Azure AI Document Intelligence
    "isValid": true,
    "extractedFields": {
      "firstName": "Juan",
      "lastName": "Pérez",
      "documentNumber": "12345678"
    },
    "confidence": 0.92
  }
}

// Índices:
db.documents.createIndex({ familyId: 1 });
db.documents.createIndex({ status: 1, uploadedAt: -1 });
```

---

## 3. Modelo de Deep Learning — OCR de comprobantes

### 3.1. Objetivo

Recibir la foto de un comprobante bancario boliviano (BNB, Mercantil, FIE, Tigo Money, etc.) y extraer automáticamente:
- Nombre del banco
- Monto pagado
- Fecha y hora
- Número de referencia
- Concepto del pago

### 3.2. Arquitectura del modelo

Se trabaja con un enfoque de **dos etapas**:

**Etapa 1 — OCR base con TrOCR:**
Se usa el modelo pre-entrenado `microsoft/trocr-base-printed` de Microsoft, que ya sabe leer texto impreso en general. Este modelo es un Transformer que combina un encoder de imagen (ViT) con un decoder de texto.

**Etapa 2 — Extracción de campos estructurados con NER:**
Sobre el texto crudo extraído por TrOCR, se aplica un modelo de Named Entity Recognition (NER) basado en BERT que identifica qué token es el banco, cuál es el monto, cuál es la fecha, etc.

### 3.3. Estrategia de obtención del dataset

Aquí está el problema más grande del proyecto: **no existe un dataset público de comprobantes bancarios bolivianos**. Tenés tres caminos:

#### Camino 1 — Dataset propio (lo más realista para el proyecto académico)

Recolectá entre 200 y 500 imágenes de comprobantes bancarios bolivianos:
- Pediles a familiares, amigos y conocidos que te envíen fotos de recibos (BNB, Mercantil, BUN, BISA, Económico, FIE).
- Buscá imágenes en Google Images con queries como `"comprobante de pago BNB Bolivia"`, `"recibo Banco Mercantil Santa Cruz"`, `"Tigo Money comprobante"`.
- Capturá pantallazos de apps bancarias bolivianas con pagos de prueba.

Luego etiquetá manualmente cada imagen usando una herramienta como **Label Studio** (open source). El formato del etiquetado debe ser:

```json
{
  "image": "receipt_001.jpg",
  "ocr_text": "BANCO NACIONAL DE BOLIVIA COMPROBANTE DE PAGO Bs. 850.00 ...",
  "entities": [
    { "start": 0,  "end": 24, "label": "BANK" },
    { "start": 47, "end": 53, "label": "AMOUNT" },
    { "start": 60, "end": 70, "label": "DATE" },
    { "start": 95, "end": 105, "label": "REFERENCE" }
  ]
}
```

#### Camino 2 — Dataset internacional como base + transfer learning

Si no llegás a las 200 imágenes propias, podés empezar con un dataset internacional grande de recibos y luego hacer fine-tuning con las pocas imágenes bolivianas que tengas:

- **SROIE 2019** (Scanned Receipts OCR and Information Extraction): https://rrc.cvc.uab.es/?ch=13 — 1000 recibos escaneados con anotaciones de monto, fecha, vendedor.
- **CORD** (Consolidated Receipt Dataset): https://github.com/clovaai/cord — 1000 recibos con anotaciones detalladas en formato JSON.
- **ICDAR-SROIE**: variante competitiva con anotaciones más ricas.

El modelo aprende primero la estructura general de recibos y luego se especializa en los bolivianos con tus pocas imágenes propias.

#### Camino 3 — Generación sintética de datos

Para complementar, podés generar comprobantes sintéticos con Python: usando PIL/Pillow crear imágenes que simulen recibos bancarios bolivianos con datos aleatorios pero realistas. Esto multiplica tu dataset y le da al modelo mayor diversidad.

```python
# Pseudocódigo para generación sintética
from PIL import Image, ImageDraw, ImageFont
import random

def generate_synthetic_receipt():
    img = Image.new('RGB', (600, 800), 'white')
    draw = ImageDraw.Draw(img)
    bank = random.choice(['BNB', 'MERCANTIL SANTA CRUZ', 'FIE', 'BISA'])
    amount = random.randint(500, 2000)
    date = f"{random.randint(1,28):02d}/{random.randint(1,12):02d}/2025"
    reference = f"{random.randint(10**9, 10**10-1)}"
    draw.text((50, 50), bank, fill='black')
    draw.text((50, 200), f"Bs. {amount}.00", fill='black')
    draw.text((50, 250), date, fill='black')
    draw.text((50, 300), f"Ref: {reference}", fill='black')
    return img, {"bank": bank, "amount": amount, "date": date, "reference": reference}
```

### 3.4. Pipeline de entrenamiento

```
1. Carga y preprocesamiento
   - Redimensionar a 384x384 (entrada de TrOCR)
   - Normalización
   - Data augmentation: rotación, brillo, contraste, ruido gaussiano

2. Fine-tuning de TrOCR
   - Cargar microsoft/trocr-base-printed
   - Reemplazar la cabeza de salida
   - Entrenar con learning rate bajo (1e-5)
   - 10-20 epochs
   - Validación con 20% del dataset

3. Entrenamiento del NER sobre el texto extraído
   - Cargar bert-base-multilingual-cased
   - Tokenizar y alinear con etiquetas BIO
   - Fine-tuning para identificar BANK, AMOUNT, DATE, REFERENCE
   - 5-10 epochs

4. Guardar modelos en /models/trocr_bolivia/ y /models/bert_receipt_ner/
5. Registrar en model_registry
```

### 3.5. Estructura del código

```
ms-ia/app/ml/ocr/
├── receipt_analyzer.py        # clase principal: analyze(image_bytes) -> ReceiptData
├── preprocessor.py            # resize, normalización, augmentation
├── postprocessor.py           # convierte el output del NER a campos estructurados
├── training/
│   ├── prepare_dataset.py     # carga imágenes y anotaciones
│   ├── fine_tune_trocr.py     # entrena el modelo OCR
│   ├── train_ner.py           # entrena el modelo NER
│   └── evaluate.py            # métricas: accuracy por campo, CER
└── data/
    ├── raw/                   # imágenes originales recolectadas
    ├── synthetic/             # imágenes generadas sintéticamente
    └── annotations/           # archivos JSON con etiquetas
```

---

## 4. Modelo de ML Supervisado — Predicción de mora

### 4.1. Objetivo

Para cada familia y cada mes, predecir si pagará tarde (después del día de gracia) o a tiempo. La salida es un número entre 0 y 1 que representa la probabilidad de mora.

### 4.2. Algoritmo elegido

**LightGBM** (Gradient Boosting). Razones:
- Funciona excelente con datos tabulares (que es lo que tenemos).
- Es rápido tanto en entrenamiento como en inferencia.
- Maneja bien valores faltantes.
- Da buena interpretabilidad (feature importance).
- Requiere menos hiperparámetros que XGBoost.

Si LightGBM no estuviera disponible, las alternativas serían **XGBoost** o **Random Forest** de scikit-learn.

### 4.3. Features (variables de entrada)

```python
FEATURES = [
    # Historial de pagos del padre
    'avg_days_late_last_3_months',     # promedio de días de retraso
    'max_days_late_ever',               # peor retraso histórico
    'months_paid_on_time_ratio',        # % de meses pagados a tiempo
    'consecutive_late_payments',        # cuántos meses seguidos pagó tarde
    'has_paid_annual_ever',             # 1 si pagó alguna vez el año completo

    # Comportamiento de pago
    'preferred_payment_method_qr',      # one-hot encoding
    'preferred_payment_method_stripe',
    'preferred_payment_method_blockchain',
    'avg_payment_day_of_month',         # día promedio del mes en que paga
    'uses_mobile_app',                  # 1 si usa app móvil

    # Contexto familiar
    'num_students',                     # cuántos hijos tiene
    'years_enrolled',                   # antigüedad
    'has_discount',                     # tiene descuento activo

    # Contexto temporal
    'month',                            # mes actual (1-12)
    'is_after_carnaval',                # febrero/marzo
    'months_remaining_year',
]

TARGET = 'will_be_late_next_month'      # 0 o 1
```

### 4.4. Estrategia de obtención del dataset

Como tampoco tenés datos reales del colegio, hay tres caminos:

#### Camino 1 — Generación de dataset sintético realista (recomendado)

Crear un script que genere ~5000 familias ficticias con historial de pagos coherente:

```python
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_family_history(family_id, num_months=24):
    """Genera historial de pagos de una familia ficticia."""

    # Asignamos un perfil aleatorio a la familia
    profile = np.random.choice(
        ['puntual', 'regular', 'irregular', 'moroso'],
        p=[0.30, 0.40, 0.20, 0.10]
    )

    payments = []
    for month_offset in range(num_months):
        month_date = datetime(2024, 1, 1) + timedelta(days=30 * month_offset)
        due_day = 10

        # Cada perfil tiene su distribución de días de retraso
        if profile == 'puntual':
            days_late = np.random.normal(-3, 1.5)       # paga antes
        elif profile == 'regular':
            days_late = np.random.normal(3, 2)           # entre día 5-15
        elif profile == 'irregular':
            days_late = np.random.normal(8, 8)           # alta varianza
        else:  # moroso
            days_late = np.random.normal(20, 10)         # paga muy tarde

        payments.append({
            'family_id': family_id,
            'month': month_date.month,
            'year': month_date.year,
            'days_late': max(-15, days_late),
            'paid': np.random.random() > (0.02 if profile != 'moroso' else 0.15),
            'profile': profile  # ← útil para validar el clustering después
        })
    return payments

# Generar 5000 familias
all_payments = []
for fid in range(5000):
    all_payments.extend(generate_family_history(fid))
df = pd.DataFrame(all_payments)
df.to_csv('data/synthetic_payments.csv', index=False)
```

Luego, sobre este dataset sintético, calcular todas las features y la variable objetivo, y entrenar el modelo. La gracia es que como vos diseñás la distribución de los perfiles, sabés que el modelo **debe** aprender a distinguirlos, lo cual valida que el pipeline funciona.

#### Camino 2 — Dataset público similar

Hay datasets de scoring crediticio que podés adaptar al problema:

- **Lending Club Dataset** (Kaggle): https://www.kaggle.com/datasets/wordsforthewise/lending-club — historial de créditos con etiqueta de incumplimiento. Las features son distintas pero el patrón de aprendizaje es el mismo.
- **Credit Card Default Dataset** (UCI ML Repository): https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients — 30000 clientes con historial de pagos mensuales y etiqueta binaria de default.
- **Give Me Some Credit** (Kaggle): https://www.kaggle.com/c/GiveMeSomeCredit — predicción de mora en préstamos.

El segundo es el más útil porque su estructura (historial mensual de pagos + variable binaria) es casi idéntica a la nuestra. Podés usarlo como base de prueba mientras desarrollás el pipeline y luego reemplazarlo con tus datos sintéticos bolivianos.

#### Camino 3 — Datos reales anónimos

Si conseguís contacto con un colegio dispuesto a entregarte un export anónimo de su sistema de cobranza (sin nombres, solo IDs y fechas), ese sería el oro. Pero suele ser difícil por confidencialidad.

### 4.5. Pipeline de entrenamiento

```
1. Cargar el dataset
   - Sintético propio o público adaptado
   - Train/test split 80/20 con stratify por la variable objetivo

2. Feature engineering
   - Calcular las features para cada familia y mes
   - Encoding: one-hot para métodos de pago
   - Scaling: no es estrictamente necesario para LightGBM

3. Entrenamiento
   - LightGBM con early stopping
   - Cross-validation 5-fold
   - Hyperparameter tuning con Optuna (opcional)

4. Evaluación
   - AUC-ROC (métrica principal)
   - Precision @ top-30 (qué tan bien identifica a los morosos en el top de riesgo)
   - F1 score
   - Confusion matrix

5. Guardar modelo
   - models/mora_predictor/v1.0.0/model.pkl
   - Registrar en MongoDB collection model_registry
```

### 4.6. Estructura del código

```
ms-ia/app/ml/supervised/
├── mora_predictor.py          # clase MoraPredictor: predict(family_features) -> risk_score
├── feature_engineering.py     # construye features desde payment_events
├── training/
│   ├── prepare_dataset.py     # genera o carga el dataset
│   ├── train_model.py         # entrena LightGBM
│   ├── evaluate_model.py      # métricas y matriz de confusión
│   └── retrain_pipeline.py    # script para reentrenamiento semanal
└── data/
    ├── synthetic_payments.csv  # dataset sintético generado
    └── features_dataset.csv    # features pre-calculadas
```

---

## 5. Modelo de ML No Supervisado — Segmentación de familias

### 5.1. Objetivo

Agrupar a las familias en 4 clusters según su comportamiento histórico de pago, sin necesidad de etiquetas previas. Los clusters deseados son:

- **Cluster 0 — Puntual Estrella:** siempre paga antes del día 5.
- **Cluster 1 — Regular:** paga entre día 5 y 15, sin incidentes.
- **Cluster 2 — Irregular:** alta variabilidad mes a mes.
- **Cluster 3 — Moroso Crónico:** paga sistemáticamente después del día 15 o acumula meses sin pagar.

### 5.2. Algoritmo elegido

**K-Means** con k=4. Razones:
- Es el algoritmo de clustering más conocido y fácil de explicar.
- Funciona bien cuando los clusters son aproximadamente esféricos.
- Es rápido y escalable a miles de familias.
- Para validar k=4 usaremos el método del codo y el análisis de silueta.

Si los clusters fueran muy irregulares en forma, las alternativas serían **DBSCAN** o **GaussianMixture**.

### 5.3. Features para clustering

A diferencia del modelo supervisado, acá las features son agregadas por familia (no por mes):

```python
CLUSTERING_FEATURES = [
    'avg_payment_day',           # día promedio del mes en que paga
    'std_dev_payment_day',       # dispersión (qué tan irregular es)
    'mora_incidence',            # % de meses con mora
    'annual_payer_score',        # 1 si paga anualmente, 0 si no
    'method_consistency',        # qué tan consistente es con el método de pago
    'months_active'              # antigüedad en meses
]
```

### 5.4. Estrategia de obtención del dataset

**Usás exactamente el mismo dataset sintético** que generaste para el modelo supervisado. La gran ventaja es que como vos diseñaste los 4 perfiles, podés validar que el K-Means realmente los descubre solo (sin haberle dicho cuáles son).

Cuando entrenes el K-Means, vas a poder cruzar la columna `profile` (que vos asignaste al generar los datos) con la columna `cluster` que predice el modelo, y verificar que la coincidencia es alta. Si lo es, el modelo funciona; si no, hay que ajustar las features o el preprocesamiento.

### 5.5. Pipeline de entrenamiento

```
1. Cargar dataset
   - Mismo dataset sintético del modelo supervisado
   - Agregar las features a nivel familia (no a nivel pago individual)

2. Preprocesamiento
   - StandardScaler para normalizar (K-Means es sensible a la escala)
   - Eliminar familias con menos de 6 meses de historial

3. Determinar k óptimo
   - Método del codo (inertia vs k para k=2..8)
   - Análisis de silueta para cada k
   - Confirmar k=4 con ambos métodos

4. Entrenar K-Means
   - n_clusters=4, random_state=42, n_init=20
   - Asignar cluster a cada familia

5. Etiquetar clusters
   - Analizar las características de cada cluster (avg_payment_day, mora_incidence)
   - Asignar nombres legibles (PUNTUAL_ESTRELLA, REGULAR, IRREGULAR, MOROSO_CRONICO)

6. Validar contra los perfiles sintéticos originales
   - Cross-tab entre profile (real) y cluster (predicho)
   - Confusion matrix
   - Si la accuracy >85%, el modelo es bueno

7. Guardar modelo
   - models/family_clusterer/v1.0.0/kmeans.pkl
   - models/family_clusterer/v1.0.0/scaler.pkl
   - Registrar en model_registry
```

### 5.6. Estructura del código

```
ms-ia/app/ml/unsupervised/
├── family_clusterer.py        # clase FamilyClusterer: predict(family_features) -> cluster
├── feature_aggregator.py      # agrega features a nivel familia desde payment_events
├── training/
│   ├── prepare_dataset.py
│   ├── find_optimal_k.py      # método del codo + silhouette
│   ├── train_clusters.py      # entrena K-Means
│   ├── label_clusters.py      # asigna nombres legibles
│   └── validate_clusters.py   # cruza contra perfiles reales
└── data/
    └── family_features_aggregated.csv
```

---

## 6. Orden de implementación recomendado

### Semana 1 — Setup e infraestructura
- Configurar las colecciones de MongoDB.
- Crear los endpoints REST básicos en FastAPI (health, upload de documento).
- Conectar con MongoDB y verificar lecturas/escrituras.

### Semana 2 — ML Supervisado (el más rápido de prototipar)
- Generar dataset sintético de 5000 familias.
- Implementar feature engineering.
- Entrenar LightGBM, validar métricas.
- Crear endpoint `GET /ai/family/{id}/risk-score`.
- Guardar predicciones en colección `predictions`.

### Semana 3 — ML No Supervisado
- Agregar features a nivel familia desde el mismo dataset sintético.
- Determinar k óptimo (validar k=4).
- Entrenar K-Means.
- Validar contra perfiles reales.
- Crear endpoint `GET /ai/family/{id}/cluster`.

### Semana 4 — Deep Learning (el más complejo)
- Recolectar imágenes de comprobantes (mínimo 100).
- Generar imágenes sintéticas (mínimo 300).
- Fine-tuning de TrOCR.
- Entrenar NER para extracción de campos.
- Crear endpoint `POST /ai/receipt/analyze`.

### Semana 5 — Integración y pulido
- Conectar con MS-Gestión para enriquecer las respuestas GraphQL.
- Implementar gestión documental con S3.
- Tests de integración.
- Documentación final.

---

## 7. Datasets recomendados (resumen rápido)

| Modelo | Dataset principal | URL / Fuente | Tamaño |
|---|---|---|---|
| OCR (Deep Learning) | SROIE 2019 | https://rrc.cvc.uab.es/?ch=13 | 1000 recibos |
| OCR (Deep Learning) | CORD | https://github.com/clovaai/cord | 1000 recibos |
| OCR (complemento) | Tus imágenes propias | Familiares, amigos, Google Images | 200-500 imágenes |
| OCR (complemento) | Imágenes sintéticas generadas con Pillow | Script propio | Ilimitadas |
| ML Supervisado | Credit Card Default | https://archive.ics.uci.edu/dataset/350/ | 30000 clientes |
| ML Supervisado | Dataset sintético propio | Script generador en Python | 5000 familias |
| ML No Supervisado | Mismo dataset sintético | Reutilizado del supervisado | 5000 familias |

---

## 8. Variables de entorno necesarias

```env
# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=edupay_ia

# AWS S3 (para documentos y modelos en producción)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
S3_BUCKET_DOCS=edupay-scz-docs
S3_BUCKET_MODELS=edupay-scz-models

# Modelos ML
MODELS_PATH=/app/models                 # ruta local en producción

# JWT (valida tokens del API Gateway)
JWT_SECRET=cambiar_en_produccion

# App
APP_PORT=8000
ENVIRONMENT=development
```

---

## 9. Dependencias clave (requirements.txt)

```txt
# Web
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9

# MongoDB
motor==3.4.0
pymongo==4.7.0

# ML — Tabular
lightgbm==4.3.0
scikit-learn==1.5.0
pandas==2.2.2
numpy==1.26.4

# ML — Deep Learning
torch==2.3.0
transformers==4.41.0
Pillow==10.3.0

# AWS
boto3==1.34.69

# Utilidades
python-jose[cryptography]==3.3.0    # JWT
pydantic==2.7.1
pydantic-settings==2.2.1

# Testing
pytest==8.2.0
pytest-asyncio==0.23.7
httpx==0.27.0
```

---

## 10. Migración futura a DynamoDB

Para que la migración sea indolora más adelante, seguí estas reglas al diseñar las colecciones:

1. **Cada documento debe poder identificarse por un par (partition_key, sort_key)**. En MongoDB usá esos campos como índice compuesto. Por ejemplo: `(familyId, predictionDate)` para `predictions`.
2. **Evitá consultas que requieran JOINs** o referencias entre colecciones. Si necesitás datos de otra colección, duplicalos en el documento (denormalización).
3. **No uses operadores avanzados de MongoDB** como `$lookup`, `$graphLookup`, etc. DynamoDB no los tiene.
4. **Abstrae el acceso a datos detrás de un repositorio**. Así, cuando migrés, solo cambiás la implementación del repositorio:

```python
# repositories/prediction_repository.py

class PredictionRepository:
    async def save(self, prediction: dict) -> str: ...
    async def find_by_family(self, family_id: str) -> list: ...
    async def find_latest(self, family_id: str) -> dict: ...

# Implementación MongoDB ahora:
class MongoPredictionRepository(PredictionRepository): ...

# Implementación DynamoDB después:
class DynamoPredictionRepository(PredictionRepository): ...
```

Con este patrón, cuando llegue el momento de migrar, solo escribís la implementación de DynamoDB y el resto del código del MS-IA no cambia.
