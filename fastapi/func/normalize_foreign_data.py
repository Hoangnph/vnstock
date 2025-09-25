#!/usr/bin/env python3
"""
Normalize Foreign Trading Data to Shares
========================================

This script converts foreign trading values (VND) to shares to match volume units.
Uses average daily price (OHLC/4) for conversion.

Input: CSV with foreign_buy_val, foreign_sell_val (VND)
Output: JSON with foreign values normalized to shares (same unit as volume)
"""

import pandas as pd
import json
import math
from pathlib import Path


def normalize_foreign_data_to_shares(csv_path: str, output_json_path: str) -> None:
    """
    Use existing foreign trading volumes (shares) from CSV data.
    
    Args:
        csv_path: Path to input CSV file
        output_json_path: Path to output JSON file
    """
    # Read CSV
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} rows from {csv_path}")
    
    # Filter out non-trading days (volume = 0 or null)
    before_filter = len(df)
    df = df.dropna(subset=['volume'])  # Remove rows with null volume
    df = df[df['volume'] > 0]  # Remove rows with zero volume
    after_filter = len(df)
    print(f"Filtered out {before_filter - after_filter} non-trading days")
    print(f"Remaining {after_filter} trading days")
    
    # Use existing foreign volumes (already in shares)
    df['foreign_buy_shares'] = df['foreign_buy_vol']
    df['foreign_sell_shares'] = df['foreign_sell_vol']
    
    # Calculate net foreign shares
    df['foreign_net_shares'] = df['foreign_buy_shares'] - df['foreign_sell_shares']
    
    # Select columns for output
    output_cols = [
        'time', 'open', 'high', 'low', 'close', 'volume',
        'foreign_buy_shares', 'foreign_sell_shares', 'foreign_net_shares'
    ]
    
    # Filter to existing columns only
    available_cols = [col for col in output_cols if col in df.columns]
    df_output = df[available_cols].copy()
    
    # Convert to records
    records = df_output.to_dict(orient='records')
    
    # Deep sanitize: replace NaN/Inf with None for JSON compatibility
    for rec in records:
        for k, v in list(rec.items()):
            if isinstance(v, float):
                if math.isnan(v) or math.isinf(v):
                    rec[k] = None
    
    # Write JSON with proper formatting
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, allow_nan=False, indent=2)
    
    print(f"Wrote normalized data to {output_json_path}")
    print(f"Columns: {list(df_output.columns)}")
    
    # Show sample statistics
    print("\nSample statistics:")
    print(f"Volume range: {df['volume'].min():,.0f} - {df['volume'].max():,.0f} shares")
    print(f"Foreign buy shares range: {df['foreign_buy_shares'].min():,.0f} - {df['foreign_buy_shares'].max():,.0f} shares")
    print(f"Foreign sell shares range: {df['foreign_sell_shares'].min():,.0f} - {df['foreign_sell_shares'].max():,.0f} shares")


def main():
    """Main function to process PDR data."""
    # Paths
    csv_path = "/Users/macintoshhd/Project/Project/stockAI/output/pdr_daily_2025-01-01_to_2025-09-25.csv"
    json_path = "/Users/macintoshhd/Project/Project/stockAI/output/web/pdr_daily_normalized.json"
    
    # Ensure output directory exists
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Process data
    normalize_foreign_data_to_shares(csv_path, json_path)
    
    print(f"\n✅ Normalization complete!")
    print(f"📁 Output: {json_path}")
    print(f"🌐 Update web chart to use: pdr_daily_normalized.json")


if __name__ == "__main__":
    main()
