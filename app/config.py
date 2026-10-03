from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    model_config=SettingsConfigDict(
        env_file=".env",env_file_encoding="utf-8",extra="ignore")
    app_name: str="Support Ticket Router"
    version: str="0.1.0"
    environment:str="development"
    model_path:str="models/classifier.joblib"
    confidence_threshold:float=0.60
    database_url: str = "sqlite:///data/tickets.db"      # <-- add this
settings=Settings()
