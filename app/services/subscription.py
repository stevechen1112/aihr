"""
Subscription Plans Configuration (T4-17)

Defines plan feature matrix and limits for Free, Pro, Enterprise tiers.
"""

PLAN_MATRIX = {
    "free": {
        "display_name": "Free",
        "price_monthly_usd": 0,
        "price_yearly_usd": 0,
        "max_users": 5,
        "max_documents": 50,
        "max_storage_mb": 100,
        "monthly_query_limit": 500,
        "monthly_token_limit": 100_000,
        "features": {
            "ai_chat": True,
            "document_upload": True,
            "basic_analytics": True,
            "audit_logs": False,
            "sso": False,
            "white_label": False,
            "custom_domain": False,
            "api_access": False,
            "priority_support": False,
            "data_export": False,
            "department_management": False,
            "advanced_analytics": False,
        },
    },
    "pro": {
        "display_name": "Pro",
        "price_monthly_usd": 29,
        "price_yearly_usd": 290,
        "max_users": 50,
        "max_documents": 500,
        "max_storage_mb": 5_000,
        "monthly_query_limit": 10_000,
        "monthly_token_limit": 2_000_000,
        "features": {
            "ai_chat": True,
            "document_upload": True,
            "basic_analytics": True,
            "audit_logs": True,
            "sso": True,
            "white_label": True,
            "custom_domain": False,
            "api_access": True,
            "priority_support": True,
            "data_export": True,
            "department_management": True,
            "advanced_analytics": True,
        },
    },
    "enterprise": {
        "display_name": "Enterprise",
        "price_monthly_usd": 99,
        "price_yearly_usd": 990,
        "max_users": None,          # Unlimited
        "max_documents": None,
        "max_storage_mb": None,
        "monthly_query_limit": None,
        "monthly_token_limit": None,
        "features": {
            "ai_chat": True,
            "document_upload": True,
            "basic_analytics": True,
            "audit_logs": True,
            "sso": True,
            "white_label": True,
            "custom_domain": True,
            "api_access": True,
            "priority_support": True,
            "data_export": True,
            "department_management": True,
            "advanced_analytics": True,
        },
    },
}


def get_plan(plan_name: str) -> dict:
    """Get plan config by name. Falls back to 'free'."""
    return PLAN_MATRIX.get(plan_name, PLAN_MATRIX["free"])


def get_plan_feature(plan_name: str, feature: str) -> bool:
    """Check if a feature is available for a plan."""
    plan = get_plan(plan_name)
    return plan["features"].get(feature, False)


def get_plan_limit(plan_name: str, limit_name: str) -> int | None:
    """Get a numeric limit for a plan. None = unlimited."""
    plan = get_plan(plan_name)
    return plan.get(limit_name)


def get_upgrade_suggestion(current_plan: str, feature: str) -> str | None:
    """Suggest which plan to upgrade to for a given feature."""
    if get_plan_feature(current_plan, feature):
        return None  # Already available

    for plan_name in ("pro", "enterprise"):
        if get_plan_feature(plan_name, feature):
            plan = get_plan(plan_name)
            return (
                f"升級至 {plan['display_name']} 方案即可使用此功能"
                f"（${plan['price_monthly_usd']}/月）"
            )
    return None
