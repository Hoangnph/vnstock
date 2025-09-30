#!/usr/bin/env python3
"""
StockAI Database API Runner
Run the FastAPI application for StockAI database

This script starts the FastAPI application with proper configuration
and logging for the StockAI database API.

Author: StockAI Team
Version: 1.0.0
"""

import asyncio
import logging
import sys
import uvicorn
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.api.fastapi_app import app

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the FastAPI application"""
    try:
        logger.info("🚀 Starting StockAI Database API...")
        
        # Configuration
        host = "0.0.0.0"
        port = 8000
        reload = True
        log_level = "info"
        
        logger.info(f"📡 API will be available at: http://{host}:{port}")
        logger.info(f"📚 API documentation at: http://{host}:{port}/docs")
        logger.info(f"🔧 ReDoc documentation at: http://{host}:{port}/redoc")
        
        # Run the application
        uvicorn.run(
            "database.api.fastapi_app:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("⏹️ API server stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start API server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
