# Ví dụ sử dụng Analytis

Thư mục này chứa các ví dụ thực tế về cách sử dụng module `analytis` cho phân tích kỹ thuật cổ phiếu.

## Các ví dụ có sẵn

### 1. `single-symbol-analysis.py`
Ví dụ phân tích một mã cổ phiếu với các cấu hình khác nhau.

**Tính năng:**
- Phân tích cơ bản với cấu hình mặc định
- Phân tích với cấu hình tùy chỉnh
- So sánh kết quả với nhiều cấu hình
- Phân tích với lưu trữ database

**Cách chạy:**
```bash
cd /Users/macintoshhd/Project/Project/stockAI/docs/analytis/examples
python single-symbol-analysis.py
```

### 2. `batch-analysis.py`
Ví dụ phân tích hàng loạt nhiều mã cổ phiếu.

**Tính năng:**
- Phân tích hàng loạt cơ bản
- Phân tích với nhiều cấu hình
- Phân tích bất đồng bộ
- Phân tích với lưu trữ database
- Xuất kết quả ra JSON

**Cách chạy:**
```bash
cd /Users/macintoshhd/Project/Project/stockAI/docs/analytis/examples
python batch-analysis.py
```

### 3. `configuration-management.py`
Ví dụ quản lý cấu hình phân tích.

**Tính năng:**
- Tạo cấu hình tùy chỉnh
- Kiểm thử cấu hình
- So sánh cấu hình
- Lưu/tải cấu hình
- Tối ưu cấu hình

**Cách chạy:**
```bash
cd /Users/macintoshhd/Project/Project/stockAI/docs/analytis/examples
python configuration-management.py
```

### 4. `database-integration.py`
Ví dụ tích hợp với database.

**Tính năng:**
- Kiểm tra kết nối database
- Phân tích với lưu trữ database
- Truy vấn lịch sử phân tích
- Truy vấn theo cấu hình
- Truy vấn tín hiệu theo hành động
- Thống kê hiệu suất
- Xuất dữ liệu database
- Dọn dẹp dữ liệu cũ

**Cách chạy:**
```bash
cd /Users/macintoshhd/Project/Project/stockAI/docs/analytis/examples
python database-integration.py
```

## Yêu cầu hệ thống

### Dependencies
- Python 3.8+
- pandas
- numpy
- sqlalchemy
- asyncpg
- asyncio

### Database
- PostgreSQL 12+
- TimescaleDB (khuyến nghị)
- Schema `stockai` với các bảng cần thiết

### Cấu hình
- File cấu hình database trong `database/api/database.py`
- Dữ liệu cổ phiếu trong bảng `stock_prices`

## Cấu trúc thư mục

```
examples/
├── README.md                           # Tài liệu này
├── single-symbol-analysis.py          # Phân tích một mã
├── batch-analysis.py                  # Phân tích hàng loạt
├── configuration-management.py        # Quản lý cấu hình
├── database-integration.py            # Tích hợp database
├── config_scalping.json              # Cấu hình scalping
├── config_swing.json                 # Cấu hình swing
├── config_position.json              # Cấu hình position
├── config_momentum.json              # Cấu hình momentum
├── all_configs.json                  # Tất cả cấu hình
├── batch_basic_results.json          # Kết quả phân tích cơ bản
├── batch_configs_results.json        # Kết quả phân tích cấu hình
├── batch_async_results.json          # Kết quả phân tích bất đồng bộ
└── database_export.json              # Xuất dữ liệu database
```

## Hướng dẫn sử dụng

### 1. Chuẩn bị môi trường

```bash
# Cài đặt dependencies
pip install -r requirements.txt

# Khởi tạo database
python database/scripts/create_modular_analysis_tables.py
```

### 2. Chạy ví dụ cơ bản

```bash
# Phân tích một mã
python single-symbol-analysis.py

# Phân tích hàng loạt
python batch-analysis.py
```

### 3. Quản lý cấu hình

```bash
# Tạo và kiểm thử cấu hình
python configuration-management.py
```

### 4. Tích hợp database

```bash
# Phân tích với database
python database-integration.py
```

## Kết quả mong đợi

### Phân tích một mã
- Thông tin dữ liệu (số điểm, thời gian)
- Danh sách tín hiệu (mua/bán, sức mạnh, điểm số)
- Tóm tắt tín hiệu (tổng, mua, bán, mạnh, điểm TB)
- So sánh với các cấu hình khác

### Phân tích hàng loạt
- Kết quả cho từng mã
- Thống kê tổng quan
- Top mã có nhiều tín hiệu
- Xuất kết quả ra JSON

### Quản lý cấu hình
- Các cấu hình chiến lược (scalping, swing, position, momentum)
- So sánh hiệu suất
- Tối ưu tham số
- Lưu/tải cấu hình

### Tích hợp database
- Lưu trữ kết quả phân tích
- Truy vấn lịch sử
- Thống kê hiệu suất
- Xuất dữ liệu

## Xử lý lỗi

### Lỗi thường gặp

1. **ModuleNotFoundError**
   - Kiểm tra Python path
   - Cài đặt dependencies

2. **Database connection error**
   - Kiểm tra cấu hình database
   - Khởi tạo schema

3. **No data error**
   - Kiểm tra dữ liệu cổ phiếu
   - Kiểm tra thời gian phân tích

### Debug

```bash
# Chạy với debug
python -u single-symbol-analysis.py 2>&1 | tee debug.log

# Kiểm tra database
python database/scripts/check_database.py
```

## Tùy chỉnh

### Thay đổi mã cổ phiếu
Sửa biến `symbol` trong các file ví dụ:

```python
symbol = "PDR"  # Thay đổi mã cổ phiếu
```

### Thay đổi thời gian
Sửa biến `start_date` và `end_date`:

```python
start_date = end_date - timedelta(days=90)  # Thay đổi số ngày
```

### Thay đổi cấu hình
Sửa các tham số trong `AnalysisConfig`:

```python
config = AnalysisConfig(
    min_score_threshold=15.0,  # Thay đổi ngưỡng
    lookback_days=120          # Thay đổi thời gian
)
```

## Đóng góp

Để thêm ví dụ mới:

1. Tạo file Python mới trong thư mục `examples/`
2. Thêm docstring mô tả chức năng
3. Thêm vào `README.md`
4. Test với dữ liệu thực tế

## Liên hệ

Nếu có vấn đề hoặc câu hỏi, vui lòng tạo issue hoặc liên hệ team phát triển.
