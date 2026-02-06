"""Create all database tables"""
import logging
from app.db.base_class import Base
from app.db.session import engine
# Import all models so they are registered with Base.metadata
from app.models import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    logger.info("Creating all database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("All tables created successfully!")

if __name__ == "__main__":
    create_tables()
