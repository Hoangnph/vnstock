#!/usr/bin/env python3
"""
Test script cho CII Intraday Service
"""

import asyncio
import sys
from pathlib import Path

# Thêm thư mục gốc vào Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi.services.cii_intraday_service import CIIIntradayService

async def test_service():
    """Test service functionality"""
    print("=== Testing CII Intraday Service ===")
    
    # Tạo service instance
    service = CIIIntradayService(symbol="CII", interval="5m")
    
    # Test 1: Kiểm tra thị trường có mở không
    print(f"1. Market open: {service.is_market_open()}")
    
    # Test 2: Tính thời gian chạy tiếp theo
    next_run = service.get_next_run_time()
    print(f"2. Next run time: {next_run}")
    
    # Test 3: Lấy dữ liệu một lần
    print("3. Testing data fetch...")
    data = await service.fetch_intraday_data()
    
    if data:
        print(f"   ✅ Data fetched successfully")
        print(f"   📊 Close price: {data.get('close', 'N/A')}")
        print(f"   📊 Volume: {data.get('volume', 'N/A')}")
        print(f"   📊 Time: {data.get('time', 'N/A')}")
        
        # Test 4: Lưu dữ liệu
        print("4. Testing data save...")
        service.save_data(data)
        service.save_to_csv(data)
        print("   ✅ Data saved successfully")
        
        # Test 5: Session summary
        print("5. Testing session summary...")
        summary = service.get_session_summary()
        print(f"   📋 Summary: {summary}")
        
    else:
        print("   ❌ Failed to fetch data")
    
    print("=== Test completed ===")

def test_market_hours():
    """Test market hours logic"""
    print("\n=== Testing Market Hours ===")
    
    service = CIIIntradayService()
    
    # Test các thời điểm khác nhau
    test_times = [
        "08:30",  # Trước giờ mở
        "09:30",  # Trong phiên sáng
        "12:00",  # Giờ nghỉ trưa
        "14:00",  # Trong phiên chiều
        "16:00",  # Sau giờ đóng
    ]
    
    for time_str in test_times:
        # Mock datetime.now() để test
        from datetime import datetime, time
        hour, minute = map(int, time_str.split(":"))
        test_time = time(hour, minute)
        
        # Kiểm tra logic
        is_open = False
        if service.market_open <= test_time <= service.lunch_start:
            is_open = True
        elif service.lunch_end <= test_time <= service.market_close:
            is_open = True
        
        print(f"   {time_str}: {'🟢 Open' if is_open else '🔴 Closed'}")

if __name__ == "__main__":
    print("CII Intraday Service Test Suite")
    print("================================")
    
    # Test market hours
    test_market_hours()
    
    # Test service functionality
    asyncio.run(test_service())
    
    print("\n✅ All tests completed!")
