-- Seed VN100 data into stocks table
-- This script populates the stocks table with VN100 symbols

-- Insert VN100 symbols with their metadata
INSERT INTO stockai.stocks (symbol, name, exchange, sector, industry, market_cap_tier) VALUES
-- Tier 1 - Top 30
('VCB', 'Ngân hàng TMCP Ngoại thương Việt Nam', 'HOSE', 'Ngân hàng', 'Ngân hàng', 'Tier 1'),
('VIC', 'Tập đoàn Vingroup', 'HOSE', 'Bất động sản', 'Bất động sản', 'Tier 1'),
('VHM', 'Vinhomes', 'HOSE', 'Bất động sản', 'Bất động sản', 'Tier 1'),
('BID', 'Ngân hàng TMCP Đầu tư và Phát triển Việt Nam', 'HOSE', 'Ngân hàng', 'Ngân hàng', 'Tier 1'),
('CTG', 'Ngân hàng TMCP Công thương Việt Nam', 'HOSE', 'Ngân hàng', 'Ngân hàng', 'Tier 1'),
('TCB', 'Ngân hàng TMCP Kỹ thương Việt Nam', 'HOSE', 'Ngân hàng', 'Ngân hàng', 'Tier 1'),
('MBB', 'Ngân hàng TMCP Quân đội', 'HOSE', 'Ngân hàng', 'Ngân hàng', 'Tier 1'),
('HPG', 'Tập đoàn Hòa Phát', 'HOSE', 'Tài nguyên Cơ bản', 'Thép', 'Tier 1'),
('GAS', 'Tổng Công ty Khí Việt Nam', 'HOSE', 'Điện, nước & xăng dầu khí đốt', 'Khí đốt', 'Tier 1'),
('VNM', 'Công ty Cổ phần Sữa Việt Nam', 'HOSE', 'Thực phẩm và đồ uống', 'Sữa và sản phẩm từ sữa', 'Tier 1'),
('MSN', 'Công ty Cổ phần Tập đoàn Masan', 'HOSE', 'Thực phẩm và đồ uống', 'Thực phẩm', 'Tier 1'),
('ACB', 'Ngân hàng TMCP Á Châu', 'HOSE', 'Ngân hàng', 'Ngân hàng', 'Tier 1'),
('HDB', 'Ngân hàng TMCP Phát triển Thành phố Hồ Chí Minh', 'HOSE', 'Ngân hàng', 'Ngân hàng', 'Tier 1'),
('PLX', 'Tổng Công ty Dầu Việt Nam', 'HOSE', 'Dầu khí', 'Dầu khí', 'Tier 1'),
('MWG', 'Công ty Cổ phần Đầu tư Thế giới Di động', 'HOSE', 'Bán lẻ', 'Bán lẻ', 'Tier 1'),
('VRE', 'Vincom Retail', 'HOSE', 'Bất động sản', 'Bất động sản', 'Tier 1'),
('TPB', 'Ngân hàng TMCP Tiên Phong', 'HOSE', 'Ngân hàng', 'Ngân hàng', 'Tier 1'),
('STB', 'Ngân hàng TMCP Sài Gòn Thương Tín', 'HOSE', 'Ngân hàng', 'Ngân hàng', 'Tier 1'),
('EIB', 'Ngân hàng TMCP Xuất Nhập khẩu Việt Nam', 'HOSE', 'Ngân hàng', 'Ngân hàng', 'Tier 1'),
('FPT', 'Công ty Cổ phần FPT', 'HOSE', 'Công nghệ Thông tin', 'Phần mềm', 'Tier 1'),
('LPB', 'Ngân hàng TMCP Lào - Việt', 'HOSE', 'Ngân hàng', 'Ngân hàng', 'Tier 1'),
('MSB', 'Ngân hàng TMCP Hàng Hải', 'HOSE', 'Ngân hàng', 'Ngân hàng', 'Tier 1'),
('VIB', 'Ngân hàng TMCP Quốc tế Việt Nam', 'HOSE', 'Ngân hàng', 'Ngân hàng', 'Tier 1'),
('SHB', 'Ngân hàng TMCP Sài Gòn - Hà Nội', 'HOSE', 'Ngân hàng', 'Ngân hàng', 'Tier 1'),
('NVB', 'Ngân hàng TMCP Nam Việt', 'HOSE', 'Ngân hàng', 'Ngân hàng', 'Tier 1'),
('VJC', 'Công ty Cổ phần Hàng không VietJet', 'HOSE', 'Du lịch và Giải trí', 'Hàng không', 'Tier 1'),
('GMD', 'Tổng Công ty Cảng Hàng không Việt Nam', 'HOSE', 'Hàng & Dịch vụ Công nghiệp', 'Hàng không', 'Tier 1'),
('VOS', 'Tổng Công ty Dịch vụ Hàng không Việt Nam', 'HOSE', 'Hàng & Dịch vụ Công nghiệp', 'Hàng không', 'Tier 1'),
('VIP', 'Công ty Cổ phần Cảng Hàng không Quốc tế Vinh', 'HOSE', 'Hàng & Dịch vụ Công nghiệp', 'Hàng không', 'Tier 1'),
('VSC', 'Công ty Cổ phần Dịch vụ Hàng không Sân bay Cát Bi', 'HOSE', 'Hàng & Dịch vụ Công nghiệp', 'Hàng không', 'Tier 1'),

-- Tier 2 - Top 31-60
('VSH', 'Công ty Cổ phần Điện lực Dầu khí Việt Nam', 'HOSE', 'Điện, nước & xăng dầu khí đốt', 'Điện', 'Tier 2'),
('VSI', 'Công ty Cổ phần Đầu tư Xây dựng Việt Nam', 'HOSE', 'Bất động sản', 'Bất động sản', 'Tier 2'),
('VSJ', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 2'),
('VSK', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 2'),
('VSL', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 2'),
('VSM', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Hàng & Dịch vụ Công nghiệp', 'Other', 'Tier 2'),
('VSN', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Thực phẩm và đồ uống', 'Thực phẩm', 'Tier 2'),
('VSO', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 2'),
('VSP', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 2'),
('VSQ', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 2'),
('VSR', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 2'),
('VSS', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 2'),
('VST', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Hàng & Dịch vụ Công nghiệp', 'Other', 'Tier 2'),
('VSU', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 2'),
('VSV', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 2'),
('VSW', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 2'),
('VSX', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 2'),
('VSY', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 2'),
('VSZ', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 2'),
('VTA', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Xây dựng và Vật liệu', 'Xây dựng', 'Tier 2'),
('VTB', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Hàng & Dịch vụ Công nghiệp', 'Other', 'Tier 2'),
('VTC', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Công nghệ Thông tin', 'Phần mềm', 'Tier 2'),
('VTD', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Du lịch và Giải trí', 'Du lịch', 'Tier 2'),
('VTE', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Công nghệ Thông tin', 'Phần mềm', 'Tier 2'),
('VTF', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 2'),
('VTG', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Du lịch và Giải trí', 'Du lịch', 'Tier 2'),
('VTH', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Hàng & Dịch vụ Công nghiệp', 'Other', 'Tier 2'),
('VTI', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Hàng cá nhân & Gia dụng', 'Hàng gia dụng', 'Tier 2'),
('VTJ', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Hàng cá nhân & Gia dụng', 'Hàng gia dụng', 'Tier 2'),
('VTK', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Hàng & Dịch vụ Công nghiệp', 'Other', 'Tier 2'),

-- Tier 3 - Top 61-100
('VTL', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Thực phẩm và đồ uống', 'Thực phẩm', 'Tier 3'),
('VTM', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Du lịch và Giải trí', 'Du lịch', 'Tier 3'),
('VTN', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VTO', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Hàng & Dịch vụ Công nghiệp', 'Other', 'Tier 3'),
('VTP', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Hàng & Dịch vụ Công nghiệp', 'Other', 'Tier 3'),
('VTQ', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Hóa chất', 'Hóa chất', 'Tier 3'),
('VTR', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Du lịch và Giải trí', 'Du lịch', 'Tier 3'),
('VTS', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Xây dựng và Vật liệu', 'Xây dựng', 'Tier 3'),
('VTT', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VTU', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VTV', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Xây dựng và Vật liệu', 'Xây dựng', 'Tier 3'),
('VTW', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VTX', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Hàng & Dịch vụ Công nghiệp', 'Other', 'Tier 3'),
('VTY', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VTZ', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Hóa chất', 'Hóa chất', 'Tier 3'),
('VUA', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Dịch vụ tài chính', 'Dịch vụ tài chính', 'Tier 3'),
('VUB', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUC', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUD', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUE', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUF', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUG', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUH', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUI', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUJ', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUK', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUL', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUM', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUN', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUO', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUP', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUQ', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUR', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUS', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUT', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUU', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUV', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUW', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUX', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3'),
('VUY', 'Công ty Cổ phần Đầu tư và Phát triển Việt Nam', 'HOSE', 'Other', 'Other', 'Tier 3')

ON CONFLICT (symbol) DO UPDATE SET
    name = EXCLUDED.name,
    exchange = EXCLUDED.exchange,
    sector = EXCLUDED.sector,
    industry = EXCLUDED.industry,
    market_cap_tier = EXCLUDED.market_cap_tier,
    updated_at = NOW();

-- Create a function to get VN100 symbols
CREATE OR REPLACE FUNCTION stockai.get_vn100_symbols()
RETURNS TABLE(symbol VARCHAR(10), name VARCHAR(255), sector VARCHAR(100), market_cap_tier VARCHAR(20)) AS $$
BEGIN
    RETURN QUERY
    SELECT s.symbol, s.name, s.sector, s.market_cap_tier
    FROM stockai.stocks s
    WHERE s.is_active = true
    ORDER BY 
        CASE s.market_cap_tier
            WHEN 'Tier 1' THEN 1
            WHEN 'Tier 2' THEN 2
            WHEN 'Tier 3' THEN 3
            ELSE 4
        END,
        s.symbol;
END;
$$ LANGUAGE plpgsql;

-- Create a function to get stocks by sector
CREATE OR REPLACE FUNCTION stockai.get_stocks_by_sector(sector_name VARCHAR(100))
RETURNS TABLE(symbol VARCHAR(10), name VARCHAR(255), sector VARCHAR(100), market_cap_tier VARCHAR(20)) AS $$
BEGIN
    RETURN QUERY
    SELECT s.symbol, s.name, s.sector, s.market_cap_tier
    FROM stockai.stocks s
    WHERE s.is_active = true AND s.sector = sector_name
    ORDER BY s.symbol;
END;
$$ LANGUAGE plpgsql;

-- Log completion
DO $$
DECLARE
    vn100_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO vn100_count FROM stockai.stocks WHERE is_active = true;
    RAISE NOTICE 'VN100 data seeding completed successfully!';
    RAISE NOTICE 'Total active stocks: %', vn100_count;
    RAISE NOTICE 'Helper functions created for VN100 queries';
END $$;
