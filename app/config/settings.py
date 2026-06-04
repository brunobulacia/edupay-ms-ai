from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str
    mongodb_database: str = "edupay_ia"

    # ── RabbitMQ ───────────────────────────────────────────────────────────────
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_docs: str = "edupay-scz-docs"
    s3_bucket_models: str = "edupay-scz-models"

    models_path: str = "/app/models"
    jwt_secret: str = "cambiar_en_produccion"
    app_port: int = 8000
    environment: str = "development"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
