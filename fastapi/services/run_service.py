#!/usr/bin/env python3
"""
Script để chạy CII Intraday Service
"""

import asyncio
import sys
import signal
from pathlib import Path

# Thêm thư mục gốc vào Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi.services.cii_intraday_service import CIIIntradayService

class ServiceRunner:
    def __init__(self):
        self.service = None
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Thiết lập signal handlers để dừng service gracefully"""
        def signal_handler(signum, frame):
            print(f"\nNhận tín hiệu {signum}, đang dừng service...")
            if self.service:
                self.service.stop_service()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self):
        """Chạy service"""
        print("=== CII Intraday Service Runner ===")
        print("Nhấn Ctrl+C để dừng service")
        print("=====================================")
        
        self.service = CIIIntradayService(symbol="CII", interval="5m")
        
        try:
            await self.service.run_service()
        except KeyboardInterrupt:
            print("\nService đã được dừng bởi người dùng")
        except Exception as e:
            print(f"Lỗi khi chạy service: {e}")
        finally:
            if self.service:
                self.service.stop_service()

def main():
    """Hàm main"""
    runner = ServiceRunner()
    asyncio.run(runner.run())

if __name__ == "__main__":
    main()
