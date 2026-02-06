import logging

from app.db.session import SessionLocal
from app.crud import crud_user, crud_tenant
from app.schemas.user import UserCreate
from app.schemas.tenant import TenantCreate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db() -> None:
    db = SessionLocal()
    
    # Check if tenant exists
    tenant = crud_tenant.get_by_name(db, name="Demo Tenant")
    if not tenant:
        logger.info("Creating demo tenant")
        tenant_in = TenantCreate(
            name="Demo Tenant",
            tax_id="00000000",
            contact_name="System Admin",
            contact_email="admin@example.com",
            contact_phone="0900000000",
            status="active"
        )
        tenant = crud_tenant.create(db, obj_in=tenant_in)
    
    # Check if superuser exists
    user = crud_user.get_by_email(db, email="admin@example.com")
    if not user:
        logger.info("Creating superuser")
        user_in = UserCreate(
            email="admin@example.com",
            password="admin123",
            tenant_id=tenant.id,
            role="owner",
            full_name="Admin User"
        )
        user = crud_user.create(db, obj_in=user_in)
        # Set superuser flag directly
        user.is_superuser = True
        db.commit()
        db.refresh(user)
    
    db.close()

if __name__ == "__main__":
    logger.info("Creating initial data")
    init_db()
    logger.info("Initial data created")
