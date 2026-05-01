from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "account-service"
    database_url: str = "mysql+pymysql://account_user:account_pass@localhost:3306/account_db"
    customer_service_url: str = "http://localhost:8001"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = "banking.events"

    class Config:
        env_file = ".env"


settings = Settings()
