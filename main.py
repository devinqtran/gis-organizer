import os
import argparse
from flask import Flask
from backend.api.routes import api_bp
from backend.utils.db_utils import DatabaseManager

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app

def setup_database():
    """Set up the database."""
    db_manager = DatabaseManager()
    db_manager.create_tables()
    print("Database initialized successfully.")

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description='GIS Organizer')
    parser.add_argument('--setup-db', action='store_true', help='Set up the database')
    parser.add_argument('--run-server', action='store_true', help='Run the API server')
    parser.add_argument('--host', default='127.0.0.1', help='Server host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000, help='Server port (default: 5000)')
    
    args = parser.parse_args()
    
    if args.setup_db:
        setup_database()
    
    if args.run_server:
        app = create_app()
        app.run(host=args.host, port=args.port, debug=True)
    
    # If no arguments, show help
    if not (args.setup_db or args.run_server):
        parser.print_help()

if __name__ == '__main__':
    main()