#!/usr/bin/env python3
"""
Debug script to test pricing functionality and see the actual output.
"""

import sys
import os
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetch import fetch_rds_instances, validate_aws_credentials
from pricing import fetch_rds_pricing

def main():
    parser = argparse.ArgumentParser(description="RDS Pricing Debug Tool")
    parser.add_argument("--nocache", action="store_true", 
                      help="Force fresh data by clearing pricing cache")
    args = parser.parse_args()
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
    
    pricing = fetch_rds_pricing(rds_instances, nocache=args.nocache)
    
    print("=" * 80)
    print("\n📊 PRICING RESULTS:")
    
    for inst in rds_instances:
        key = (inst['DBInstanceIdentifier'], inst['Region'], inst['Engine'])
        price_info = pricing.get(key)
        
        print(f"\n🏷️  {inst['DBInstanceIdentifier']}:")
        print(f"    Instance Class: {inst['DBInstanceClass']}")
        print(f"    Engine: {inst['Engine']}")
        print(f"    Region: {inst['Region']}")
        print(f"    Storage: {inst.get('AllocatedStorage', 'N/A')}GB {inst.get('StorageType', 'N/A')}")
        print(f"    IOPS: {inst.get('Iops', 'N/A')}")
        
        # Show throughput information
        storage_throughput = inst.get('StorageThroughput', 0)
        storage_type = inst.get('StorageType', '').lower()
        print(f"    Throughput: {storage_throughput} MB/s")
        
        # Calculate billed throughput for gp3 (above 125 MB/s baseline)
        if storage_type == 'gp3' and storage_throughput and storage_throughput > 125:
            billed_throughput = storage_throughput - 125
            print(f"    📊 gp3 Baseline: 125 MB/s (free)")
            print(f"    📊 Billed Throughput: {billed_throughput} MB/s (above baseline)")
        elif storage_type == 'gp3':
            print(f"    📊 gp3 Baseline: All throughput within free 125 MB/s")
        elif storage_type == 'gp2':
            print(f"    📊 gp2: Throughput included in storage cost")
        
        if price_info:
            if isinstance(price_info, dict):
                instance_cost = price_info.get('instance') or 0
                storage_cost = price_info.get('storage') or 0
                iops_cost = price_info.get('iops') or 0
                throughput_cost = price_info.get('throughput') or 0
                total_cost = price_info.get('total') or 0
                print(f"    💲 Instance:    ${instance_cost:.4f}/hr")
                print(f"    💲 Storage:     ${storage_cost:.4f}/hr")
                print(f"    💲 IOPS:        ${iops_cost:.4f}/hr")
                print(f"    💲 Throughput:  ${throughput_cost:.4f}/hr")
                print(f"    💲 TOTAL:       ${total_cost:.4f}/hr")
                
                # Show monthly costs for better perspective
                monthly_throughput = throughput_cost * 24 * 30.42  # Average month
                if throughput_cost > 0:
                    print(f"    📅 Throughput (monthly): ${monthly_throughput:.2f}")
            else:
                price_val = price_info or 0
                print(f"    💲 Price: ${price_val:.4f}/hr")
        else:
            print("    ❌ No pricing data found")

if __name__ == "__main__":
    main()