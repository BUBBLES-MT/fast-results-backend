"""
Script ya kuunda database tables zote.
Run hii script mara ya kwanza tu.
"""

from app.core.database import engine, Base
from app.models import *  # Import all models

def init_database():
    print("🚀 Starting database initialization...")
    print("📦 Creating all tables...")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
        
        # Print all table names
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\n📊 Tables created ({len(tables)}):")
        for table in tables:
            print(f"   - {table}")
            
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise

if __name__ == "__main__":
    init_database()