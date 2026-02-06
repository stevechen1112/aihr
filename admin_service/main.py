"""
Admin Service 主入口
====================
Re-export app 方便 uvicorn 直接指定：
    uvicorn admin_service.main:app --port 8001
"""

from admin_service import app

__all__ = ["app"]
