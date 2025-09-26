#!/usr/bin/env python3
"""
CII Intraday Trading Service
Tự động lấy thông tin giao dịch CII theo mốc 5 phút trong phiên
"""

import asyncio
import logging
import json
import os
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from vnstock import Vnstock

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fastapi/services/logs/cii_intraday.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CIIIntradayService:
    def __init__(self, symbol: str = "CII", interval: str = "5m"):
        self.symbol = symbol
        self.interval = interval
        self.vnstock = Vnstock()
        self.data_dir = Path("fastapi/services/data")
        self.logs_dir = Path("fastapi/services/logs")
        
        # Tạo thư mục nếu chưa có
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Thời gian phiên giao dịch VN
        self.market_open = time(9, 0)  # 9:00 AM
        self.market_close = time(15, 0)  # 3:00 PM
        self.lunch_start = time(11, 30)  # 11:30 AM
        self.lunch_end = time(13, 0)  # 1:00 PM
        
        # Trạng thái service
        self.is_running = False
        self.current_session_data = []
        
    def is_market_open(self) -> bool:
        """Kiểm tra xem thị trường có đang mở không"""
        now = datetime.now().time()
        
        # Kiểm tra thứ trong tuần (0=Monday, 6=Sunday)
        weekday = datetime.now().weekday()
        if weekday >= 5:  # Thứ 7, Chủ nhật
            return False
            
        # Kiểm tra giờ giao dịch
        if self.market_open <= now <= self.lunch_start:
            return True
        elif self.lunch_end <= now <= self.market_close:
            return True
        else:
            return False
    
    def get_next_run_time(self) -> datetime:
        """Tính thời gian chạy tiếp theo"""
        now = datetime.now()
        current_time = now.time()
        
        # Nếu đang trong phiên sáng (9:00-11:30)
        if self.market_open <= current_time < self.lunch_start:
            next_run = now.replace(second=0, microsecond=0)
            # Làm tròn đến mốc 5 phút tiếp theo
            minutes_to_add = 5 - (now.minute % 5)
            if minutes_to_add == 5:
                minutes_to_add = 0
            next_run += timedelta(minutes=minutes_to_add)
            return next_run
            
        # Nếu đang trong giờ nghỉ trưa (11:30-13:00)
        elif self.lunch_start <= current_time < self.lunch_end:
            # Chờ đến 13:00
            next_run = now.replace(hour=13, minute=0, second=0, microsecond=0)
            return next_run
            
        # Nếu đang trong phiên chiều (13:00-15:00)
        elif self.lunch_end <= current_time < self.market_close:
            next_run = now.replace(second=0, microsecond=0)
            # Làm tròn đến mốc 5 phút tiếp theo
            minutes_to_add = 5 - (now.minute % 5)
            if minutes_to_add == 5:
                minutes_to_add = 0
            next_run += timedelta(minutes=minutes_to_add)
            return next_run
            
        # Nếu ngoài giờ giao dịch, chờ đến 9:00 ngày mai
        else:
            tomorrow = now + timedelta(days=1)
            next_run = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            return next_run
    
    async def fetch_intraday_data(self) -> Optional[Dict]:
        """Lấy dữ liệu giao dịch trong phiên"""
        try:
            logger.info(f"Đang lấy dữ liệu {self.symbol} - {self.interval}")
            
            # Lấy dữ liệu từ VCI
            data = self.vnstock.stock(symbol=self.symbol).quote.history(
                start_date=datetime.now().strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d"),
                interval=self.interval,
                provider="vci"
            )
            
            if data is not None and not data.empty:
                # Lấy dữ liệu mới nhất
                latest_data = data.iloc[-1].to_dict()
                
                # Thêm thông tin metadata
                latest_data.update({
                    'symbol': self.symbol,
                    'interval': self.interval,
                    'fetch_time': datetime.now().isoformat(),
                    'data_source': 'vci'
                })
                
                logger.info(f"Lấy được dữ liệu {self.symbol}: {latest_data.get('close', 'N/A')}")
                return latest_data
            else:
                logger.warning(f"Không lấy được dữ liệu {self.symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu {self.symbol}: {str(e)}")
            return None
    
    def save_data(self, data: Dict) -> None:
        """Lưu dữ liệu vào file"""
        try:
            # Tạo tên file theo ngày
            today = datetime.now().strftime("%Y-%m-%d")
            filename = f"{self.symbol}_intraday_{today}.json"
            filepath = self.data_dir / filename
            
            # Đọc dữ liệu hiện có
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            else:
                existing_data = []
            
            # Thêm dữ liệu mới
            existing_data.append(data)
            
            # Lưu lại
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Đã lưu dữ liệu vào {filepath}")
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu: {str(e)}")
    
    def save_to_csv(self, data: Dict) -> None:
        """Lưu dữ liệu vào CSV để dễ phân tích"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            filename = f"{self.symbol}_intraday_{today}.csv"
            filepath = self.data_dir / filename
            
            # Tạo DataFrame từ dữ liệu
            df_new = pd.DataFrame([data])
            
            # Đọc dữ liệu hiện có
            if filepath.exists():
                df_existing = pd.read_csv(filepath)
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            else:
                df_combined = df_new
            
            # Lưu CSV
            df_combined.to_csv(filepath, index=False, encoding='utf-8')
            logger.info(f"Đã lưu CSV vào {filepath}")
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu CSV: {str(e)}")
    
    async def process_data(self) -> None:
        """Xử lý dữ liệu và lưu vào file"""
        if not self.is_market_open():
            logger.info("Thị trường đang đóng, bỏ qua việc lấy dữ liệu")
            return
        
        # Lấy dữ liệu
        data = await self.fetch_intraday_data()
        
        if data:
            # Lưu vào JSON
            self.save_data(data)
            
            # Lưu vào CSV
            self.save_to_csv(data)
            
            # Thêm vào session data
            self.current_session_data.append(data)
            
            # Log thông tin quan trọng
            logger.info(f"=== CII Data Update ===")
            logger.info(f"Time: {data.get('time', 'N/A')}")
            logger.info(f"Open: {data.get('open', 'N/A')}")
            logger.info(f"High: {data.get('high', 'N/A')}")
            logger.info(f"Low: {data.get('low', 'N/A')}")
            logger.info(f"Close: {data.get('close', 'N/A')}")
            logger.info(f"Volume: {data.get('volume', 'N/A')}")
            logger.info(f"========================")
    
    async def run_service(self) -> None:
        """Chạy service chính"""
        logger.info(f"Khởi động CII Intraday Service - {self.symbol} ({self.interval})")
        self.is_running = True
        
        while self.is_running:
            try:
                # Xử lý dữ liệu
                await self.process_data()
                
                # Tính thời gian chạy tiếp theo
                next_run = self.get_next_run_time()
                wait_seconds = (next_run - datetime.now()).total_seconds()
                
                if wait_seconds > 0:
                    logger.info(f"Chờ {wait_seconds:.0f} giây đến {next_run.strftime('%H:%M:%S')}")
                    await asyncio.sleep(wait_seconds)
                else:
                    # Nếu đã quá thời gian, chờ 5 giây rồi chạy lại
                    await asyncio.sleep(5)
                    
            except KeyboardInterrupt:
                logger.info("Nhận tín hiệu dừng, đang thoát...")
                break
            except Exception as e:
                logger.error(f"Lỗi trong service: {str(e)}")
                await asyncio.sleep(30)  # Chờ 30 giây trước khi thử lại
        
        self.is_running = False
        logger.info("CII Intraday Service đã dừng")
    
    def stop_service(self) -> None:
        """Dừng service"""
        self.is_running = False
        logger.info("Đã gửi tín hiệu dừng service")
    
    def get_session_summary(self) -> Dict:
        """Lấy tóm tắt phiên giao dịch hiện tại"""
        if not self.current_session_data:
            return {"message": "Chưa có dữ liệu trong phiên"}
        
        # Tính toán thống kê
        closes = [d.get('close', 0) for d in self.current_session_data if d.get('close')]
        volumes = [d.get('volume', 0) for d in self.current_session_data if d.get('volume')]
        
        summary = {
            "symbol": self.symbol,
            "session_date": datetime.now().strftime("%Y-%m-%d"),
            "total_records": len(self.current_session_data),
            "first_price": closes[0] if closes else None,
            "last_price": closes[-1] if closes else None,
            "price_change": closes[-1] - closes[0] if len(closes) > 1 else 0,
            "price_change_pct": ((closes[-1] - closes[0]) / closes[0] * 100) if len(closes) > 1 and closes[0] > 0 else 0,
            "min_price": min(closes) if closes else None,
            "max_price": max(closes) if closes else None,
            "total_volume": sum(volumes) if volumes else 0,
            "avg_volume": sum(volumes) / len(volumes) if volumes else 0,
            "last_update": self.current_session_data[-1].get('fetch_time') if self.current_session_data else None
        }
        
        return summary

# Hàm chính để chạy service
async def main():
    service = CIIIntradayService(symbol="CII", interval="5m")
    
    try:
        await service.run_service()
    except KeyboardInterrupt:
        service.stop_service()

if __name__ == "__main__":
    asyncio.run(main())
