#!/usr/bin/env python3
"""
Simple focused benchmark for Smart RDS Viewer
Quick performance checks for specific components
"""

import time
import sys
from fetch import fetch_rds_instances, validate_aws_credentials
from metrics import fetch_storage_metrics
from pricing import fetch_rds_pricing, clear_pricing_cache


def simple_timer(func, *args, **kwargs):
    """Simple timing function"""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    duration = end - start
    print(f"⏱️  {func.__name__}: {duration:.3f}s")
    return result, duration


def main():
    print("🚀 Smart RDS Viewer - Quick Benchmark")
    print("-" * 40)
    
    if not validate_aws_credentials():
        print("❌ AWS credentials not configured")
        sys.exit(1)
    
    total_time = 0
    
    # Test RDS fetching
    print("1️⃣  Fetching RDS instances...")
    rds_instances, duration = simple_timer(fetch_rds_instances)
    total_time += duration
    print(f"   Found: {len(rds_instances)} instances")
    
    if not rds_instances:
        print("⚠️  No RDS instances found")
        return
    
    # Test metrics fetching
    print("\n2️⃣  Fetching CloudWatch metrics...")
    metrics, duration = simple_timer(fetch_storage_metrics, rds_instances)
    total_time += duration
    metrics_count = len([k for k, v in metrics.items() if v is not None])
    print(f"   Retrieved: {metrics_count}/{len(rds_instances)} metrics")
    
    # Test pricing (fresh)
    print("\n3️⃣  Fetching pricing (fresh)...")
    clear_pricing_cache()
    pricing_fresh, fresh_duration = simple_timer(fetch_rds_pricing, rds_instances, True)
    total_time += fresh_duration
    
    # Test pricing (cached)
    print("\n4️⃣  Fetching pricing (cached)...")
    pricing_cached, cached_duration = simple_timer(fetch_rds_pricing, rds_instances, False)
    
    # Summary
    print(f"\n📊 RESULTS:")
    print(f"   Total time: {total_time:.3f}s")
    print(f"   Cache speedup: {fresh_duration/cached_duration:.1f}x")
    print(f"   Instances/second: {len(rds_instances)/total_time:.1f}")
    
    # Performance rating
    if total_time < 5:
        print("🟢 Performance: Excellent")
    elif total_time < 15:
        print("🟡 Performance: Good")
    else:
        print("🔴 Performance: Needs optimization")


if __name__ == "__main__":
    main()