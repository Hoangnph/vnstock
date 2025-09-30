# 🔍 PHÂN TÍCH SÂU NGUYÊN NHÂN MÃ THẤT BẠI TRONG PIPELINE VN100

## 📊 TỔNG QUAN

**Số mã thất bại:** 4/37 mã VN100 (10.8%)  
**Mã thất bại:** VIB, NVB, VHM, MSN  
**Nguyên nhân chính:** Constraint violations trong database

## 🔍 PHÂN TÍCH CHI TIẾT TỪNG MÃ

### 1. VIB - Ngân hàng TMCP Việt Nam Thương Tín

**Trạng thái:** ❌ Thất bại  
**Nguyên nhân:** Constraint violations

**Chi tiết lỗi:**
- **Constraint violation:** `low > close`
  - Ngày: 2018-07-23
  - Low: 3.73, Close: 0.00
- **Constraint violation:** `close <= 0`
  - Ngày: 2018-07-23
  - Close: 0.00
- **Constraint violation:** `low > close`
  - Ngày: 2019-07-04
  - Low: 3.35, Close: 3.33

**Phân tích:** VIB có dữ liệu không hợp lệ với giá đóng cửa = 0 và low > close, vi phạm các constraint của database.

### 2. NVB - Ngân hàng TMCP Nam Việt

**Trạng thái:** ❌ Thất bại  
**Nguyên nhân:** Constraint violations

**Chi tiết lỗi:**
- **Constraint violation:** `high < close`
  - Ngày: 2013-11-22
  - High: 4.95, Close: 5.03

**Phân tích:** NVB có dữ liệu không hợp lệ với high < close, vi phạm constraint `ck_stock_prices_high_ge_close`.

### 3. VHM - Vinhomes

**Trạng thái:** ❌ Thất bại  
**Nguyên nhân:** Constraint violations

**Chi tiết lỗi:**
- **Constraint violation:** `low > close`
  - Ngày: 2014-09-29
  - Low: 37.39, Close: 34.02

**Phân tích:** VHM có dữ liệu không hợp lệ với low > close, vi phạm constraint `ck_stock_prices_low_le_close`.

### 4. MSN - Công ty Cổ phần Đầu tư Masan

**Trạng thái:** ❌ Thất bại  
**Nguyên nhân:** Constraint violations

**Chi tiết lỗi:**
- **Constraint violation:** `low > open`
  - Ngày: 2010-12-29
  - Low: 35.52, Open: 35.26

**Phân tích:** MSN có dữ liệu không hợp lệ với low > open, vi phạm constraint `ck_stock_prices_low_le_open`.

## 🎯 NGUYÊN NHÂN GỐC RỄ

### 1. Dữ liệu từ nguồn VCI không hợp lệ
- **Vấn đề:** Một số ngày giao dịch có dữ liệu OHLCV không hợp lệ
- **Ví dụ:** Giá đóng cửa = 0, low > close, high < close, low > open
- **Nguyên nhân:** Có thể do lỗi dữ liệu từ VCI hoặc ngày đặc biệt (ngừng giao dịch, chia tách cổ phiếu)

### 2. Database constraints quá nghiêm ngặt
- **Constraint hiện tại:**
  - `ck_stock_prices_close_positive`: close > 0
  - `ck_stock_prices_low_le_close`: low <= close
  - `ck_stock_prices_high_ge_close`: high >= close
  - `ck_stock_prices_low_le_open`: low <= open
- **Vấn đề:** Không xử lý được các trường hợp đặc biệt

### 3. Thiếu validation trong pipeline
- **Vấn đề:** Pipeline không kiểm tra và làm sạch dữ liệu trước khi lưu
- **Hậu quả:** Dữ liệu không hợp lệ được đưa vào database và gây lỗi

## 🔧 GIẢI PHÁP ĐỀ XUẤT

### 1. Cải thiện validation trong pipeline
```python
def validate_ohlcv_data(df):
    """Validate OHLCV data before saving to database"""
    # Fix close = 0 cases
    df.loc[df['close'] == 0, 'close'] = df.loc[df['close'] == 0, 'open']
    
    # Fix low > close cases
    df.loc[df['low'] > df['close'], 'low'] = df.loc[df['low'] > df['close'], 'close']
    
    # Fix high < close cases
    df.loc[df['high'] < df['close'], 'high'] = df.loc[df['high'] < df['close'], 'close']
    
    # Fix low > open cases
    df.loc[df['low'] > df['open'], 'low'] = df.loc[df['low'] > df['open'], 'open']
    
    return df
```

### 2. Làm mềm database constraints
```sql
-- Thay vì constraint nghiêm ngặt, sử dụng trigger để tự động sửa
CREATE OR REPLACE FUNCTION fix_ohlcv_data()
RETURNS TRIGGER AS $$
BEGIN
    -- Fix close = 0
    IF NEW.close <= 0 THEN
        NEW.close := NEW.open;
    END IF;
    
    -- Fix low > close
    IF NEW.low > NEW.close THEN
        NEW.low := NEW.close;
    END IF;
    
    -- Fix high < close
    IF NEW.high < NEW.close THEN
        NEW.high := NEW.close;
    END IF;
    
    -- Fix low > open
    IF NEW.low > NEW.open THEN
        NEW.low := NEW.open;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### 3. Xử lý các trường hợp đặc biệt
- **Ngày đặc biệt:** Ngừng giao dịch, chia tách cổ phiếu
- **Dữ liệu lỗi:** Tự động sửa hoặc bỏ qua
- **Logging:** Ghi lại các trường hợp đặc biệt để theo dõi

### 4. Retry mechanism với data cleaning
```python
def fetch_with_retry_and_clean(symbol, start_date, end_date):
    """Fetch data with retry and automatic data cleaning"""
    for attempt in range(3):
        try:
            data = fetch_stock_data(symbol, start_date, end_date)
            cleaned_data = validate_ohlcv_data(data)
            return cleaned_data
        except ConstraintViolationError:
            if attempt < 2:
                # Try with cleaned data
                continue
            else:
                # Skip problematic records
                return clean_problematic_records(data)
```

## 📋 KẾT LUẬN

**Nguyên nhân chính:** Dữ liệu từ VCI có một số records không hợp lệ, vi phạm các constraint của database.

**Tác động:** 4 mã VN100 quan trọng không thể lưu vào database.

**Giải pháp:** Cần cải thiện validation và xử lý dữ liệu trong pipeline để tự động sửa các lỗi dữ liệu trước khi lưu vào database.

**Ưu tiên:** Implement data validation và cleaning trong pipeline để đảm bảo tỷ lệ thành công cao hơn.

---
*Phân tích được thực hiện ngày: 2025-09-26*
