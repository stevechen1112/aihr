"""
多區域部署設定（T4-19）
========================

定義各區域的基礎設施配置，包含：
- 資料庫連線
- Redis 連線
- Pinecone Index
- Celery Broker
- 合規資訊
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class RegionConfig:
    """單一區域的基礎設施配置"""

    code: str                        # 區域代碼：ap, us, eu, jp
    name: str                        # 顯示名稱
    display_name_zh: str             # 中文名稱

    # 資料庫
    db_host: str = "db"
    db_port: int = 5432

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379

    # Pinecone
    pinecone_environment: str = ""
    pinecone_index_prefix: str = ""

    # Celery
    celery_broker_url: str = ""

    # 合規
    data_residency: str = ""         # 資料落地說明
    compliance_notes: str = ""       # 法規遵循備註

    # 服務端點
    api_endpoint: str = ""
    cdn_endpoint: str = ""


# ---------------------------------------------------------------------------
# 區域定義
# ---------------------------------------------------------------------------
REGIONS: Dict[str, RegionConfig] = {
    "ap": RegionConfig(
        code="ap",
        name="Asia Pacific (Taiwan)",
        display_name_zh="亞太區（台灣）",
        db_host=os.getenv("AP_DB_HOST", "db"),
        db_port=int(os.getenv("AP_DB_PORT", "5432")),
        redis_host=os.getenv("AP_REDIS_HOST", "redis"),
        redis_port=int(os.getenv("AP_REDIS_PORT", "6379")),
        pinecone_environment=os.getenv("AP_PINECONE_ENV", "asia-southeast1-gcp"),
        pinecone_index_prefix="ap-unihr",
        celery_broker_url=os.getenv("AP_CELERY_BROKER", "redis://redis:6379/0"),
        data_residency="資料儲存於台灣 GCP asia-east1 區域",
        compliance_notes="符合台灣個資法 (PDPA) 要求",
        api_endpoint="https://api-ap.unihr.com",
        cdn_endpoint="https://cdn-ap.unihr.com",
    ),
    "us": RegionConfig(
        code="us",
        name="United States",
        display_name_zh="美國",
        db_host=os.getenv("US_DB_HOST", "db-us"),
        db_port=int(os.getenv("US_DB_PORT", "5432")),
        redis_host=os.getenv("US_REDIS_HOST", "redis-us"),
        redis_port=int(os.getenv("US_REDIS_PORT", "6379")),
        pinecone_environment=os.getenv("US_PINECONE_ENV", "us-east1-gcp"),
        pinecone_index_prefix="us-unihr",
        celery_broker_url=os.getenv("US_CELERY_BROKER", "redis://redis-us:6379/0"),
        data_residency="Data stored in US GCP us-east1 region",
        compliance_notes="SOC 2 Type II compliant infrastructure",
        api_endpoint="https://api-us.unihr.com",
        cdn_endpoint="https://cdn-us.unihr.com",
    ),
    "eu": RegionConfig(
        code="eu",
        name="Europe",
        display_name_zh="歐洲",
        db_host=os.getenv("EU_DB_HOST", "db-eu"),
        db_port=int(os.getenv("EU_DB_PORT", "5432")),
        redis_host=os.getenv("EU_REDIS_HOST", "redis-eu"),
        redis_port=int(os.getenv("EU_REDIS_PORT", "6379")),
        pinecone_environment=os.getenv("EU_PINECONE_ENV", "eu-west1-gcp"),
        pinecone_index_prefix="eu-unihr",
        celery_broker_url=os.getenv("EU_CELERY_BROKER", "redis://redis-eu:6379/0"),
        data_residency="Data stored in EU GCP europe-west1 region (Frankfurt)",
        compliance_notes="GDPR compliant — data never leaves EU",
        api_endpoint="https://api-eu.unihr.com",
        cdn_endpoint="https://cdn-eu.unihr.com",
    ),
    "jp": RegionConfig(
        code="jp",
        name="Japan",
        display_name_zh="日本",
        db_host=os.getenv("JP_DB_HOST", "db-jp"),
        db_port=int(os.getenv("JP_DB_PORT", "5432")),
        redis_host=os.getenv("JP_REDIS_HOST", "redis-jp"),
        redis_port=int(os.getenv("JP_REDIS_PORT", "6379")),
        pinecone_environment=os.getenv("JP_PINECONE_ENV", "asia-northeast1-gcp"),
        pinecone_index_prefix="jp-unihr",
        celery_broker_url=os.getenv("JP_CELERY_BROKER", "redis://redis-jp:6379/0"),
        data_residency="データは日本 GCP asia-northeast1 リージョンに保存",
        compliance_notes="APPI (Act on Protection of Personal Information) 準拠",
        api_endpoint="https://api-jp.unihr.com",
        cdn_endpoint="https://cdn-jp.unihr.com",
    ),
}

# 預設區域
DEFAULT_REGION = os.getenv("DEFAULT_REGION", "ap")

# 支援的區域列表
SUPPORTED_REGIONS = list(REGIONS.keys())


def get_region_config(region_code: str) -> RegionConfig:
    """取得區域設定，不存在時回傳預設區域"""
    return REGIONS.get(region_code, REGIONS[DEFAULT_REGION])


def get_all_regions() -> list:
    """取得所有區域摘要（供 API 回傳）"""
    return [
        {
            "code": r.code,
            "name": r.name,
            "display_name_zh": r.display_name_zh,
            "data_residency": r.data_residency,
            "compliance_notes": r.compliance_notes,
        }
        for r in REGIONS.values()
    ]
