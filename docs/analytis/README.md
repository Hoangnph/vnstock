# StockAI Analysis System Documentation

## Tổng quan

Hệ thống phân tích StockAI được thiết kế theo kiến trúc mô-đun, tách biệt rõ ràng giữa việc tính toán chỉ số kỹ thuật, cấu hình chấm điểm, và kết quả phân tích. Điều này cho phép linh hoạt trong việc thử nghiệm và tối ưu hóa các chiến lược phân tích.

## Cấu trúc thư mục

```
docs/analytis/
├── README.md                    # Tài liệu tổng quan
├── database-schema.md           # Chi tiết schema database
├── engines/                     # Tài liệu các engine
│   ├── indicator-engine.md      # Engine tính toán chỉ số
│   ├── scoring-engine.md        # Engine chấm điểm
│   └── signal-engine.md         # Engine tạo tín hiệu
├── repositories/                # Tài liệu repositories
│   ├── config-repository.md     # Repository cấu hình
│   ├── indicator-repository.md  # Repository chỉ số
│   ├── analysis-repository.md   # Repository kết quả
│   └── signal-repository.md     # Repository tín hiệu
├── usage-guides/                # Hướng dẫn sử dụng
│   ├── basic-usage.md           # Sử dụng cơ bản
│   ├── configuration.md         # Cấu hình hệ thống
│   ├── experimentation.md       # Thử nghiệm và tối ưu
│   └── troubleshooting.md       # Khắc phục sự cố
└── examples/                    # Ví dụ thực tế
    ├── single-symbol-analysis.py
    ├── batch-analysis.py
    ├── config-comparison.py
    └── signal-analysis.py
```

## Kiến trúc hệ thống

### 1. Engines (Mô-đun xử lý)

- **IndicatorEngine**: Tính toán các chỉ số kỹ thuật thuần túy
- **ScoringEngine**: Chấm điểm và đánh giá tín hiệu
- **SignalEngine**: Tạo và phân loại tín hiệu giao dịch

### 2. Repositories (Truy cập dữ liệu)

- **ConfigRepository**: Quản lý cấu hình phân tích
- **IndicatorRepository**: Lưu trữ kết quả tính toán chỉ số
- **AnalysisRepository**: Quản lý kết quả phân tích
- **SignalRepository**: Lưu trữ tín hiệu giao dịch

### 3. Database Schema (Cấu trúc dữ liệu)

- **analysis_configurations**: Cấu hình hệ thống
- **indicator_calculations**: Kết quả tính toán chỉ số
- **analysis_results**: Kết quả phân tích tổng hợp
- **signal_results**: Tín hiệu giao dịch chi tiết
- **analysis_experiments**: Theo dõi thí nghiệm

## Tính năng chính

### ✅ Tách biệt trách nhiệm
- Tính toán chỉ số độc lập với chấm điểm
- Cấu hình linh hoạt và có thể tái sử dụng
- Kết quả phân tích có thể truy vết được

### ✅ Linh hoạt thử nghiệm
- Thử nghiệm nhiều cấu hình khác nhau
- So sánh hiệu quả giữa các chiến lược
- Theo dõi lịch sử thí nghiệm

### ✅ Hiệu suất cao
- Lưu trữ chỉ số tính toán để tái sử dụng
- Batch processing cho nhiều mã cổ phiếu
- Indexing tối ưu cho truy vấn nhanh

### ✅ Mở rộng dễ dàng
- Thêm chỉ số mới không ảnh hưởng hệ thống cũ
- Plugin architecture cho scoring rules
- API nhất quán cho tất cả operations

## Bắt đầu nhanh

### 1. Cài đặt

```bash
# Cài đặt dependencies
pip install -r requirements.txt

# Tạo database schema
python database/scripts/create_modular_analysis_tables.py
```

### 2. Phân tích cơ bản

```python
from analytis.analysis_engine import AnalysisEngine, AnalysisConfig

# Tạo engine với cấu hình mặc định
engine = AnalysisEngine()

# Phân tích một mã cổ phiếu
result = engine.analyze_symbol("PDR", "2025-01-01", "2025-10-01")

# Xem kết quả
print(f"Tổng tín hiệu: {len(result.signals)}")
for signal in result.signals[-5:]:  # 5 tín hiệu gần nhất
    print(f"{signal.timestamp.date()}: {signal.action.value} {signal.strength.value}")
```

### 3. Phân tích với database

```python
from analytis.analysis_engine_db import DatabaseIntegratedAnalysisEngine

# Tạo engine tích hợp database
engine = DatabaseIntegratedAnalysisEngine()

# Phân tích và lưu vào database
result = await engine.analyze_symbol("PDR", "2025-01-01", "2025-10-01")

# Xem thông tin database
print(f"Analysis Result ID: {result.analysis_result_id}")
print(f"Indicator Config ID: {result.indicator_config_id}")
```

## Tài liệu chi tiết

### 📊 [Database Schema](database-schema.md)
Chi tiết về cấu trúc database, relationships, và indexing

### 🔧 [Engines](engines/)
Tài liệu chi tiết về các engine xử lý

### 💾 [Repositories](repositories/)
Hướng dẫn sử dụng các repository

### 📖 [Usage Guides](usage-guides/)
Hướng dẫn sử dụng từ cơ bản đến nâng cao

### 💡 [Examples](examples/)
Ví dụ thực tế và best practices

## Hỗ trợ

- **Issues**: Tạo issue trên GitHub repository
- **Discussions**: Thảo luận trong GitHub Discussions
- **Documentation**: Cập nhật tài liệu trong thư mục `docs/`

## Đóng góp

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

## License

MIT License - Xem file LICENSE để biết thêm chi tiết.
