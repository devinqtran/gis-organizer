# config.py
import os

class Config:
    """Base configuration class."""
    # Application directory
    APP_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Database settings
    DATABASE_PATH = os.path.join(APP_DIR, 'gis_organizer.db')
    
    # API settings
    API_HOST = '127.0.0.1'
    API_PORT = 5000
    
    # Logging settings
    LOG_LEVEL = 'INFO'
    LOG_FILE = os.path.join(APP_DIR, 'gis_organizer.log')
    
    # Default directories
    DEFAULT_DATA_DIR = os.path.join(APP_DIR, 'data')
    
    # Create necessary directories if they don't exist
    @classmethod
    def initialize(cls):
        """Create necessary directories."""
        os.makedirs(cls.DEFAULT_DATA_DIR, exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    LOG_LEVEL = 'WARNING'

# Default configuration
DefaultConfig = DevelopmentConfig