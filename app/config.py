import secrets
import warnings
from typing import List, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Known insecure default keys (must never be used in production) ──
_INSECURE_KEYS = {
    "change_this",
    "change_this_to_a_secure_random_string",
    "CHANGE_THIS_PRODUCTION_SECRET_MIN_32_CHARS",
    "secret",
}


class Settings(BaseSettings):
    APP_NAME: str = "UniHR SaaS"
    APP_ENV: str = "development"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "change_this"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    ALGORITHM: str = "HS256"

    # ── First superuser (used by scripts/initial_data.py) ──
    FIRST_SUPERUSER_EMAIL: str = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "admin123"
    
    # CORS
    BACKEND_CORS_ORIGINS: str = ""

    # Core API
    CORE_API_URL: str = "http://localhost:5000"
    CORE_SERVICE_TOKEN: str = ""

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "unihr_saas"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 2   # 秒
    REDIS_SOCKET_TIMEOUT: int = 2           # 秒
    REDIS_SOCKET_KEEPALIVE: bool = True
    REDIS_HEALTH_CHECK_INTERVAL: int = 30   # 秒，redis-py 內建心跳

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_WORKER_CONCURRENCY: int = 2
    CELERY_WORKER_MAX_TASKS_PER_CHILD: int = 100
    CELERY_WORKER_MAX_MEMORY_PER_CHILD_KB: int = 524288  # 512 MB
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1
    CELERY_TASK_SOFT_TIME_LIMIT_SECONDS: int = 300
    CELERY_TASK_TIME_LIMIT_SECONDS: int = 360
    CELERY_TASK_ACKS_LATE: bool = True
    CELERY_TASK_REJECT_ON_WORKER_LOST: bool = True
    CELERY_TASK_RETRY_BACKOFF: bool = True
    CELERY_TASK_RETRY_BACKOFF_MAX_SECONDS: int = 300
    CELERY_TASK_RETRY_JITTER: bool = True
    CELERY_DOCUMENT_TASK_MAX_RETRIES: int = 3
    CELERY_URL_TASK_MAX_RETRIES: int = 2

    # 稽核留存
    AUDIT_RETENTION_YEARS: int = 7  # 關鍵事件留存年限（勞基法規建議最小 5 年）

    # Gemini（用於 Generation 回答生成 + HyDE 查詢擴展）
    LLM_BACKEND: str = "gemini"  # gemini / core
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash-preview-04-17"  # Generation 使用的模型
    LLM_TEMPERATURE: float = 0.3     # 回答生成溫度（低 = 更精確）
    LLM_MAX_TOKENS: int = 1500       # 回答最大 token 數
    LLM_MAX_INPUT_TOKENS: int = 6000    # prompts + context 合計上限（預估）
    LLM_CONTEXT_RESERVE_TOKENS: int = 1800  # 預留給模型輸出與安全緩衝
    LLM_GUARDRAIL_ENABLED: bool = True
    LLM_GUARDRAIL_BLOCK_PATTERNS: str = (
        "ignore previous instructions,"
        "system prompt,"
        "developer message,"
        "忽略上述,"
        "忽略前面,"
        "顯示提示詞,"
        "越權"
    )
    LLM_IO_SENSITIVE_FILTER_ENABLED: bool = True
    LLM_INPUT_SENSITIVE_PATTERNS: str = (
        "身分證字號,"
        "信用卡,"
        "密碼,"
        "一次性密碼,"
        "otp"
    )
    LLM_OUTPUT_SENSITIVE_PATTERNS: str = (
        "api key,"
        "secret key,"
        "password,"
        "access token,"
        "refresh token,"
        "系統提示詞,"
        "system prompt"
    )

    # Voyage AI + pgvector
    VOYAGE_API_KEY: str = ""
    VOYAGE_MODEL: str = "voyage-4-lite"
    EMBEDDING_DIMENSION: int = 1024

    # Cloudflare R2（檔案儲存）
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_ENDPOINT: str = ""
    R2_BUCKET: str = "aihr-uploads"

    # Pinecone（向量資料庫）
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "aihr-vectors"

    # LlamaParse（高品質文檔解析 — 跨頁表格、手寫 OCR、複雜佈局）
    LLAMAPARSE_API_KEY: str = ""
    LLAMAPARSE_ENABLED: bool = True  # 設為 False 可強制使用內建解析器
    LLAMAPARSE_RESULT_TYPE: str = "markdown"
    LLAMAPARSE_LANGUAGE: str = "zh-TW"
    LLAMAPARSE_AUTO_MODE: bool = True
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # Document Processing
    CHUNK_SIZE: int = 1000  # tokens
    CHUNK_OVERLAP: int = 150  # tokens
    TABLE_FULL_CHUNK_MAX_CHARS: int = 20000  # 結構化表格全文 chunk 上限
    MARKDOWN_MIN_SECTION_TOKENS: int = 80
    TEXT_MIN_SECTION_TOKENS: int = 30

    # OCR
    OCR_LANGS: str = "chi_tra+eng"

    # Retrieval
    RETRIEVAL_MODE: str = "hybrid"         # semantic / keyword / hybrid
    RETRIEVAL_MIN_SCORE: float = 0.0       # 最低相似度閾值
    RETRIEVAL_RERANK: bool = True          # 是否啟用重排序
    RETRIEVAL_CACHE_TTL: int = 300         # 快取秒數
    RETRIEVAL_TOP_K: int = 5               # 預設返回數量

    # Source arbitration (policy vs labor-law Core)
    SOURCE_PRIORITY_MODE: str = "adaptive"    # adaptive / policy_first / law_first
    POLICY_SOURCE_WEIGHT: float = 0.65         # 0.0 ~ 1.0
    LAW_SOURCE_WEIGHT: float = 0.35            # 0.0 ~ 1.0
    CONFLICT_RESOLUTION_MODE: str = "legal_floor"  # legal_floor / policy_override / law_override

    # SSO / OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    SSO_DEFAULT_REDIRECT_URI: str = "http://localhost:3001/login/callback"

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_GLOBAL_PER_IP: int = 200     # requests / minute per IP
    RATE_LIMIT_PER_USER: int = 60           # requests / minute per user
    RATE_LIMIT_PER_TENANT: int = 300        # requests / minute per tenant
    RATE_LIMIT_CHAT_PER_USER: int = 20      # chat requests / minute per user

    # PostgreSQL RLS
    RLS_ENFORCEMENT_ENABLED: bool = False

    # Admin API Network Isolation (T4-4)
    ADMIN_IP_WHITELIST_ENABLED: bool = False   # Enable in production
    ADMIN_IP_WHITELIST: str = "127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
    ADMIN_TRUSTED_PROXY_IPS: str = "127.0.0.1,::1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("LLM_BACKEND")
    @classmethod
    def _validate_llm_backend(cls, v: str) -> str:
        backend = (v or "gemini").strip().lower()
        if backend not in {"gemini", "core"}:
            raise ValueError("LLM_BACKEND must be one of: gemini, core")
        return backend

    @field_validator("SOURCE_PRIORITY_MODE")
    @classmethod
    def _validate_source_priority_mode(cls, v: str) -> str:
        mode = (v or "adaptive").strip().lower()
        if mode not in {"adaptive", "policy_first", "law_first"}:
            raise ValueError(
                "SOURCE_PRIORITY_MODE must be one of: adaptive, policy_first, law_first"
            )
        return mode

    @field_validator("CONFLICT_RESOLUTION_MODE")
    @classmethod
    def _validate_conflict_resolution_mode(cls, v: str) -> str:
        mode = (v or "legal_floor").strip().lower()
        if mode not in {"legal_floor", "policy_override", "law_override"}:
            raise ValueError(
                "CONFLICT_RESOLUTION_MODE must be one of: legal_floor, policy_override, law_override"
            )
        return mode

    @field_validator("POLICY_SOURCE_WEIGHT", "LAW_SOURCE_WEIGHT")
    @classmethod
    def _validate_source_weight(cls, v: float) -> float:
        value = float(v)
        if not (0.0 <= value <= 1.0):
            raise ValueError("source weights must be between 0.0 and 1.0")
        return value

    @model_validator(mode="after")
    def _validate_production_security(self) -> "Settings":
        """Block startup if critical secrets are insecure in production / staging."""
        if self.APP_ENV in ("production", "staging"):
            # ── SECRET_KEY ──
            if self.SECRET_KEY in _INSECURE_KEYS or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    f"SECRET_KEY is insecure ('{self.SECRET_KEY[:8]}…'). "
                    "Set a strong random key (≥ 32 chars) in .env or environment. "
                    f"Hint: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
                )
            # ── Database password ──
            if self.POSTGRES_PASSWORD in ("postgres", ""):
                raise ValueError(
                    "POSTGRES_PASSWORD is set to default 'postgres'. "
                    "Set a strong password in .env or environment."
                )
            # ── Superuser credentials ──
            if self.FIRST_SUPERUSER_EMAIL == "admin@example.com":
                warnings.warn(
                    "FIRST_SUPERUSER_EMAIL is still 'admin@example.com'. "
                    "Consider changing it for production.",
                    UserWarning,
                    stacklevel=2,
                )
            if self.FIRST_SUPERUSER_PASSWORD == "admin123":
                warnings.warn(
                    "FIRST_SUPERUSER_PASSWORD is still the default 'admin123'. "
                    "Set FIRST_SUPERUSER_PASSWORD in .env for production.",
                    UserWarning,
                    stacklevel=2,
                )
        return self

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_staging(self) -> bool:
        return self.APP_ENV == "staging"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

settings = Settings()
