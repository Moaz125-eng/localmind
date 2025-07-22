from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LOCALMIND_", env_file=".env", extra="ignore")

    data_dir: Path = Path("./localmind_data")
    database_url: str = "sqlite+aiosqlite:///./localmind_data/localmind.db"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    index_exclude: str = "venv,.venv,node_modules,.git,__pycache__,dist,build,.mypy_cache"

    @property
    def exclude_patterns(self) -> list[str]:
        return [part.strip() for part in self.index_exclude.split(",") if part.strip()]

    def ensure_data_dir(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir
