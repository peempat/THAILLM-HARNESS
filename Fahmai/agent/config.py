from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus
import os


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value in (None, ""):
        return default
    return int(value)


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value in (None, ""):
        return default
    return float(value)


def _resolve_workspace_path(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    resolved = (WORKSPACE_ROOT / path).resolve()
    if resolved.exists():
        return resolved
    for candidate in [
        WORKSPACE_ROOT / "fah-mai-the-finale-enterprise-data-agentic-showdown",
        WORKSPACE_ROOT.parent / "hack 4 fahmai" / "fah-mai-the-finale-enterprise-data-agentic-showdown",
        WORKSPACE_ROOT.parent / "fah-mai-the-finale-enterprise-data-agentic-showdown",
    ]:
        if candidate.exists():
            return candidate.resolve()
    return resolved


@dataclass(frozen=True)
class Settings:
    project_root: Path
    workspace_root: Path
    corpus_root: Path
    database_url: str
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    db_sslmode: str
    db_search_path: str
    max_retries: int = 3
    vector_top_k: int = 8
    keyword_top_k: int = 8
    max_sql_retries: int = 3
    query_timeout_sec: int = 10
    default_limit: int = 50
    local_health_url: str = "http://swarm-manager.modelharbor.com:56980/health"
    local_agent_url: str = "http://swarm-manager.modelharbor.com:56980/agent/local"
    local_ocr_url: str = "http://swarm-manager.modelharbor.com:56980/ocr"
    local_model: str = "typhoon-ai/typhoon-s-thaillm-8b-instruct-research-preview"
    local_max_tokens: int = 2048
    local_temperature: float = 0.2
    local_timeout_sec: int = 60
    llm_provider: str = "opentyphoon"
    llm_base_url: str = "https://api.opentyphoon.ai/v1"
    llm_chat_url: str = "https://api.opentyphoon.ai/v1/chat/completions"
    llm_api_key: str = ""
    llm_model: str = "typhoon-v2.5-30b-a3b-instruct"
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.2
    llm_timeout_sec: int = 90
    embedding_provider: str = "modelharbor"
    embedding_url: str = "http://swarm-manager.modelharbor.com:56980/v1/embeddings"
    embedding_model: str = "qwen3-embedding"
    embedding_timeout_sec: int = 90
    embedding_batch_size: int = 8
    vector_index_path: Path = PROJECT_ROOT / "artifacts" / "vector_index_qwen3.jsonl"

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "Settings":
        load_env_file(env_file or PROJECT_ROOT / ".env")

        host = os.environ.get("FAHMAI_DB_HOST", "0.tcp.ap.ngrok.io")
        port = _env_int("FAHMAI_DB_PORT", 26551)
        name = os.environ.get("FAHMAI_DB_NAME", "fahmai")
        user = os.environ.get("FAHMAI_DB_USER", "fahmai_app")
        password = os.environ.get("FAHMAI_DB_PASSWORD", "")
        sslmode = os.environ.get("FAHMAI_DB_SSLMODE", "disable")
        search_path = os.environ.get("FAHMAI_DB_SEARCH_PATH", "core,mart,public,rag")
        database_url = os.environ.get("FAHMAI_DATABASE_URL")
        if not database_url:
            database_url = (
                f"postgresql://{quote_plus(user)}:{quote_plus(password)}"
                f"@{host}:{port}/{name}"
            )

        corpus_root = _resolve_workspace_path(
            os.environ.get(
                "FAHMAI_CORPUS_ROOT",
                "fah-mai-the-finale-enterprise-data-agentic-showdown",
            )
        )

        return cls(
            project_root=PROJECT_ROOT,
            workspace_root=WORKSPACE_ROOT,
            corpus_root=corpus_root,
            database_url=database_url,
            db_host=host,
            db_port=port,
            db_name=name,
            db_user=user,
            db_password=password,
            db_sslmode=sslmode,
            db_search_path=search_path,
            max_retries=_env_int("FAHMAI_MAX_RETRIES", 3),
            vector_top_k=_env_int("FAHMAI_VECTOR_TOP_K", 8),
            keyword_top_k=_env_int("FAHMAI_KEYWORD_TOP_K", 8),
            max_sql_retries=_env_int("FAHMAI_MAX_SQL_RETRIES", 3),
            query_timeout_sec=_env_int("FAHMAI_QUERY_TIMEOUT_SEC", 10),
            default_limit=_env_int("FAHMAI_DEFAULT_LIMIT", 50),
            local_health_url=os.environ.get(
                "FAHMAI_LOCAL_HEALTH_URL",
                "http://swarm-manager.modelharbor.com:56980/health",
            ),
            local_agent_url=os.environ.get(
                "FAHMAI_LOCAL_AGENT_URL",
                "http://swarm-manager.modelharbor.com:56980/agent/local",
            ),
            local_ocr_url=os.environ.get(
                "FAHMAI_LOCAL_OCR_URL",
                "http://swarm-manager.modelharbor.com:56980/ocr",
            ),
            local_model=os.environ.get(
                "FAHMAI_LOCAL_MODEL",
                "typhoon-ai/typhoon-s-thaillm-8b-instruct-research-preview",
            ),
            local_max_tokens=_env_int("FAHMAI_LOCAL_MAX_TOKENS", 2048),
            local_temperature=_env_float("FAHMAI_LOCAL_TEMPERATURE", 0.2),
            local_timeout_sec=_env_int("FAHMAI_LOCAL_TIMEOUT_SEC", 60),
            llm_provider=os.environ.get("FAHMAI_LLM_PROVIDER", "opentyphoon"),
            llm_base_url=os.environ.get("FAHMAI_LLM_BASE_URL", "https://api.opentyphoon.ai/v1"),
            llm_chat_url=os.environ.get(
                "FAHMAI_LLM_CHAT_URL",
                "https://api.opentyphoon.ai/v1/chat/completions",
            ),
            llm_api_key=os.environ.get("FAHMAI_LLM_API_KEY") or os.environ.get("OPENTYPHOON_API_KEY", ""),
            llm_model=os.environ.get("FAHMAI_LLM_MODEL", "typhoon-v2.5-30b-a3b-instruct"),
            llm_max_tokens=_env_int("FAHMAI_LLM_MAX_TOKENS", 2048),
            llm_temperature=_env_float("FAHMAI_LLM_TEMPERATURE", 0.2),
            llm_timeout_sec=_env_int("FAHMAI_LLM_TIMEOUT_SEC", 90),
            embedding_provider=os.environ.get("FAHMAI_EMBEDDING_PROVIDER", "modelharbor"),
            embedding_url=os.environ.get(
                "FAHMAI_EMBEDDING_URL",
                "http://swarm-manager.modelharbor.com:56980/v1/embeddings",
            ),
            embedding_model=os.environ.get("FAHMAI_EMBEDDING_MODEL", "qwen3-embedding"),
            embedding_timeout_sec=_env_int("FAHMAI_EMBEDDING_TIMEOUT_SEC", 90),
            embedding_batch_size=_env_int("FAHMAI_EMBEDDING_BATCH_SIZE", 8),
            vector_index_path=_resolve_workspace_path(
                os.environ.get("FAHMAI_VECTOR_INDEX_PATH", "Fahmai/artifacts/vector_index_qwen3.jsonl")
            ),
        )

    @property
    def redacted_database_url(self) -> str:
        if self.db_password and self.db_password in self.database_url:
            return self.database_url.replace(self.db_password, "***")
        return self.database_url
