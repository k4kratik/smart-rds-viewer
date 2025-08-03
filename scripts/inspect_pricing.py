#!/usr/bin/env python3
"""
Inspect the actual storage and IOPS pricing data structure.
"""

from pricing import get_rds_pricing_data
import json

def main():
    print("=== Inspecting Storage and IOPS Pricing Data ===")
    
    region = "ap-south-1"
    engine = "mysql"
    
    print(f"\n📦 STORAGE PRICING DATA:")
    storage_data = get_rds_pricing_data(
        region=region, 
        engine=engine,
        filters=[{"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Database Storage"}]
    )
    
    print(f"Found {len(storage_data)} storage pricing items:")
    for i, item in enumerate(storage_data[:5]):  # Show first 5
        print(f"\n[{i}] Storage Item:")
        print(f"  Description: {item.get('Description', 'N/A')}")
        print(f"  UsageType: {item.get('UsageType', 'N/A')}")
        print(f"  Price: {item.get('Price (USD)', 'N/A')}")
        print(f"  Unit: {item.get('Unit', 'N/A')}")
        print(f"  StorageType: {item.get('StorageType', 'N/A')}")
        print(f"  Region: {item.get('Region', 'N/A')}")
    
    print(f"\n⚡ IOPS PRICING DATA:")
    iops_data = get_rds_pricing_data(
        region=region,
        engine=engine, 
        filters=[{"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Provisioned IOPS"}]
    )
    
    print(f"Found {len(iops_data)} IOPS pricing items:")
    for i, item in enumerate(iops_data[:5]):  # Show first 5
        print(f"\n[{i}] IOPS Item:")
        print(f"  Description: {item.get('Description', 'N/A')}")
        print(f"  UsageType: {item.get('UsageType', 'N/A')}")
        print(f"  Price: {item.get('Price (USD)', 'N/A')}")
        print(f"  Unit: {item.get('Unit', 'N/A')}")
        print(f"  StorageType: {item.get('StorageType', 'N/A')}")
        print(f"  Region: {item.get('Region', 'N/A')}")

if __name__ == "__main__":
    main()