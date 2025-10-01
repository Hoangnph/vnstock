# Pipeline Directory

Thư mục này chứa các pipeline chính cho việc cập nhật dữ liệu và phân tích VN100.

## Files

### 1. `vn100_analysis_pipeline.py` ⭐ **MAIN PIPELINE**
Pipeline tích hợp cập nhật dữ liệu VN100 và tính toán chỉ số phân tích tự động.

**Tính năng:**
- Cập nhật dữ liệu VN100 từ SSI API với tracking
- Tự động tính toán chỉ số phân tích cho các mã đã cập nhật
- Lưu kết quả phân tích vào database
- Hỗ trợ batch processing và incremental updates
- Báo cáo chi tiết kết quả

**Usage:**
```bash
# Chạy với cấu hình mặc định
python fastapi/pipeline/vn100_analysis_pipeline.py

# Tùy chỉnh batch size và thời gian phân tích
python fastapi/pipeline/vn100_analysis_pipeline.py --batch 5 --analysis-days 60
```

**Parameters:**
- `--batch`: Kích thước batch cho cập nhật dữ liệu (default: 3)
- `--analysis-days`: Số ngày phân tích (default: 30)

### 2. `ssi_vn100_update_with_tracking.py`
Pipeline cập nhật dữ liệu VN100 từ SSI API với hệ thống tracking.

**Tính năng:**
- Cập nhật incremental với tracking
- Tránh duplicate data
- Batch processing với rate limiting
- Báo cáo chi tiết

**Usage:**
```bash
python fastapi/pipeline/ssi_vn100_update_with_tracking.py --batch 3
```

### 3. `force_overwrite_recent.py`
Pipeline ghi đè dữ liệu gần đây cho VN100.

**Tính năng:**
- Ghi đè dữ liệu 2-3 ngày gần nhất
- Dọn dẹp duplicate
- Đảm bảo dữ liệu mới nhất

**Usage:**
```bash
python fastapi/pipeline/force_overwrite_recent.py
```

### 4. `upsert_manager.py`
Module quản lý upsert operations với duplicate prevention.

**Tính năng:**
- Upsert stock prices và foreign trades
- Tránh duplicate data
- Batch operations
- Error handling

## Workflow

### 1. Daily Update (Khuyến nghị)
```bash
# Chạy pipeline tích hợp hàng ngày
python fastapi/pipeline/vn100_analysis_pipeline.py --batch 3 --analysis-days 30
```

### 2. Data Update Only
```bash
# Chỉ cập nhật dữ liệu
python fastapi/pipeline/ssi_vn100_update_with_tracking.py --batch 5
```

### 3. Force Overwrite
```bash
# Ghi đè dữ liệu gần đây khi cần
python fastapi/pipeline/force_overwrite_recent.py
```

## Configuration

### Batch Size
- **Nhỏ (1-3)**: An toàn, ít lỗi, chậm
- **Trung bình (3-5)**: Cân bằng tốc độ và ổn định
- **Lớn (5-10)**: Nhanh, có thể gặp rate limit

### Analysis Days
- **30 ngày**: Phân tích ngắn hạn, nhanh
- **60 ngày**: Phân tích trung hạn, cân bằng
- **90+ ngày**: Phân tích dài hạn, chậm

## Monitoring

### Logs
Pipeline tự động tạo logs chi tiết:
- Tiến trình cập nhật
- Kết quả phân tích
- Lỗi và cảnh báo
- Thống kê hiệu suất

### Output Files
- `output/pipeline_results_YYYYMMDD_HHMMSS.json`: Kết quả chi tiết
- Database tables: Kết quả phân tích được lưu tự động

## Error Handling

### Common Issues
1. **Rate Limit**: Giảm batch size
2. **Network Error**: Pipeline tự động retry
3. **Database Error**: Check connection và permissions
4. **Analysis Error**: Check data availability

### Troubleshooting
```bash
# Kiểm tra database connection
python database/scripts/check_database.py

# Kiểm tra SSI API
python fastapi/func/ssi_playwright_probe.py

# Test analysis engine
python analytis/test_db_integration.py
```

## Performance

### Optimization Tips
1. **Batch Size**: Điều chỉnh theo network và API limits
2. **Analysis Days**: Giảm để tăng tốc độ
3. **Database**: Đảm bảo indexes được tạo
4. **Memory**: Monitor memory usage với batch lớn

### Expected Performance
- **100 mã VN100**: ~10-15 phút (batch=3, analysis=30 days)
- **Memory usage**: ~500MB-1GB
- **Database size**: ~50MB per 1000 records

## Integration

### Cron Job
```bash
# Cập nhật hàng ngày lúc 18:00
0 18 * * * cd /path/to/stockAI && python fastapi/pipeline/vn100_analysis_pipeline.py --batch 3 --analysis-days 30
```

### API Integration
```python
from fastapi.pipeline.vn100_analysis_pipeline import VN100AnalysisPipeline

# Sử dụng trong FastAPI
pipeline = VN100AnalysisPipeline(batch_size=3, analysis_days=30)
result = await pipeline.run_pipeline()
```

## Dependencies

### Required
- `fastapi.func.ssi_fetcher_with_tracking`
- `fastapi.func.vn100_database_loader`
- `analytis.analysis_engine_db`
- `database.api.database`
- `database.api.repositories`

### Optional
- `pandas` (for CSV fallback)
- `asyncio` (for async operations)

## Support

### Documentation
- [Analytis Documentation](../docs/analytis/)
- [Database Schema](../docs/analytis/database-schema.md)
- [Usage Guides](../docs/analytis/usage-guides/)

### Examples
- [Single Symbol Analysis](../docs/analytis/examples/single-symbol-analysis.py)
- [Batch Analysis](../docs/analytis/examples/batch-analysis.py)
- [Database Integration](../docs/analytis/examples/database-integration.py)
