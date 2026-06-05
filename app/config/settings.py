from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── DynamoDB ───────────────────────────────────────────────────────────────
    # En local apunta a DynamoDB Local; en prod queda vacío (usa endpoint AWS real)
    dynamodb_endpoint_url: str = ""
    aws_access_key_id: str = "local"
    aws_secret_access_key: str = "local"
    aws_region: str = "us-east-1"

    # ── RabbitMQ ───────────────────────────────────────────────────────────────
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"

    # ── S3 ─────────────────────────────────────────────────────────────────────
    s3_bucket_docs: str = "edupay-scz-docs"
    s3_bucket_models: str = "edupay-scz-models"

    # ── App ────────────────────────────────────────────────────────────────────
    models_path: str = "./models_store"
    jwt_secret: str = "cambiar_en_produccion"
    app_port: int = 8000
    environment: str = "development"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
