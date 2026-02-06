"""Create additional test users"""
import logging
from app.db.session import SessionLocal
from app.crud import crud_user, crud_tenant
from app.schemas.user import UserCreate
from app.schemas.tenant import TenantCreate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_users():
    db = SessionLocal()
    
    # Create a second tenant for testing
    tenant2 = crud_tenant.get_by_name(db, name="Test Company")
    if not tenant2:
        logger.info("Creating Test Company tenant")
        tenant_in = TenantCreate(
            name="Test Company",
            tax_id="12345678",
            contact_name="Test Owner",
            contact_email="owner@test.com",
            contact_phone="0912345678",
            status="active",
            plan="pro"
        )
        tenant2 = crud_tenant.create(db, obj_in=tenant_in)
    
   # Create owner user (non-superuser) for Test Company
    owner = crud_user.get_by_email(db, email="owner@test.com")
    if not owner:
        logger.info("Creating owner user")
        owner_in = UserCreate(
            email="owner@test.com",
            password="owner123",
            tenant_id=tenant2.id,
            role="owner",
            full_name="Test Owner"
        )
        owner = crud_user.create(db, obj_in=owner_in)
    
    # Create admin user for Test Company
    admin = crud_user.get_by_email(db, email="admin@test.com")
    if not admin:
        logger.info("Creating admin user")
        admin_in = UserCreate(
            email="admin@test.com",
            password="admin123",
            tenant_id=tenant2.id,
            role="admin",
            full_name="Test Admin"
        )
        admin = crud_user.create(db, obj_in=admin_in)
    
    # Create employee user for Test Company
    employee = crud_user.get_by_email(db, email="employee@test.com")
    if not employee:
        logger.info("Creating employee user")
        employee_in = UserCreate(
            email="employee@test.com",
            password="employee123",
            tenant_id=tenant2.id,
            role="employee",
            full_name="Test Employee"
        )
        employee = crud_user.create(db, obj_in=employee_in)
    
    logger.info("Test users created successfully!")
    logger.info("=" * 50)
    logger.info("Test Accounts:")
    logger.info("Superuser: admin@example.com / admin123")
    logger.info("Owner: owner@test.com / owner123")
    logger.info("Admin: admin@test.com / admin123")
    logger.info("Employee: employee@test.com / employee123")
    logger.info("=" * 50)
    
    db.close()

if __name__ == "__main__":
    create_test_users()
