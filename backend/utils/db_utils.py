# utils/db_utils.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
import os
from ..models.db_models import Base

class DatabaseManager:
    """
    Handles database connections and session management.
    """
    
    def __init__(self, db_path=None):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file (default: app directory)
        """
        if db_path is None:
            # Default to app directory
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(app_dir, 'gis_organizer.db')
        
        # Create engine
        self.engine = create_engine(f'sqlite:///{db_path}')
        
        # Create session factory
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)
    
    def create_tables(self):
        """Create all tables in the database."""
        Base.metadata.create_all(self.engine)
    
    def get_session(self):
        """Get a database session."""
        return self.Session()
    
    def close_session(self, session):
        """Close a database session."""
        session.close()