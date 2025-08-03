#!/usr/bin/env python3
"""
Debug script to test pricing functionality and see the actual output.
"""

import sys
from fetch import fetch_rds_instances, validate_aws_credentials
from pricing import fetch_rds_pricing

def main():
    print("=== RDS Pricing Debug Tool ===")
    
    if not validate_aws_credentials():
        print("ERROR: AWS credentials not valid")
        sys.exit(1)
    
    print("✅ AWS credentials validated")
    
    print("\n📡 Fetching RDS instances...")
    rds_instances = fetch_rds_instances()
    
    if not rds_instances:
        print("❌ No RDS instances found")
        sys.exit(1)
    
    print(f"✅ Found {len(rds_instances)} RDS instances:")
    for i, inst in enumerate(rds_instances):
        print(f"  {i+1}. {inst['DBInstanceIdentifier']} ({inst['DBInstanceClass']}) - {inst['Engine']} in {inst['Region']}")
    
    print(f"\n💰 Fetching pricing for {len(rds_instances)} instances...")
    print("=" * 80)
    
    pricing = fetch_rds_pricing(rds_instances)
    
    print("=" * 80)
    print("\n📊 PRICING RESULTS:")
    
    for inst in rds_instances:
        key = (inst['DBInstanceClass'], inst['Region'], inst['Engine'])
        price_info = pricing.get(key)
        
        print(f"\n🏷️  {inst['DBInstanceIdentifier']}:")
        print(f"    Instance Class: {inst['DBInstanceClass']}")
        print(f"    Engine: {inst['Engine']}")
        print(f"    Region: {inst['Region']}")
        print(f"    Storage: {inst.get('AllocatedStorage', 'N/A')}GB {inst.get('StorageType', 'N/A')}")
        print(f"    IOPS: {inst.get('Iops', 'N/A')}")
        
        if price_info:
            if isinstance(price_info, dict):
                instance_cost = price_info.get('instance') or 0
                storage_cost = price_info.get('storage') or 0
                iops_cost = price_info.get('iops') or 0
                total_cost = price_info.get('total') or 0
                print(f"    💲 Instance: ${instance_cost:.4f}/hr")
                print(f"    💲 Storage:  ${storage_cost:.4f}/hr")
                print(f"    💲 IOPS:     ${iops_cost:.4f}/hr")
                print(f"    💲 TOTAL:    ${total_cost:.4f}/hr")
            else:
                price_val = price_info or 0
                print(f"    💲 Price: ${price_val:.4f}/hr")
        else:
            print("    ❌ No pricing data found")

if __name__ == "__main__":
    main()