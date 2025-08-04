# 🚀 Smart RDS Viewer - Performance Benchmarking

A simple benchmarking tool to measure and optimize the performance of Smart RDS Viewer.

## 📋 Overview

The benchmarking tool provides a quick performance check to help you:
- Measure AWS API call performance (RDS, CloudWatch, Pricing)
- Monitor cache effectiveness
- Identify performance bottlenecks
- Get overall performance rating

## 🛠️ Setup

Ensure your AWS credentials are configured:
```bash
aws configure
# OR set environment variables:
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=your_region
```

## 🚀 Usage

### Run Performance Benchmark
```bash
make benchmark
# OR directly:
python simple_benchmark.py
```

### Example Output
```
🚀 Smart RDS Viewer - Quick Benchmark
----------------------------------------
1️⃣  Fetching RDS instances...
⏱️  fetch_rds_instances: 2.156s
   Found: 5 instances

2️⃣  Fetching CloudWatch metrics...
⏱️  fetch_storage_metrics: 3.421s
   Retrieved: 5/5 metrics

3️⃣  Fetching pricing (fresh)...
⏱️  fetch_rds_pricing: 12.847s

4️⃣  Fetching pricing (cached)...
⏱️  fetch_rds_pricing: 0.003s

📊 RESULTS:
   Total time: 18.424s
   Cache speedup: 4282.3x
   Instances/second: 0.3
🟡 Performance: Good
```

## 📊 Performance Ratings

- **🟢 Excellent**: Total time < 5 seconds
- **🟡 Good**: Total time 5-15 seconds  
- **🔴 Needs optimization**: Total time > 15 seconds

## 🔧 Optimization Tips

### Slow AWS API Calls
- Check network connectivity and AWS region
- Verify AWS credentials and permissions
- Consider using different AWS region closer to you

### Poor Cache Performance
- Ensure cache directory `/tmp` has proper permissions
- Check if cache files are being created and persist
- Verify cache isn't being cleared between runs

### High Overall Time
- Run benchmark multiple times to get consistent results
- Check system load and network conditions
- Consider running during off-peak hours for more consistent results

## 📁 Integration

Add to your workflow:
```bash
# Check performance before deployment
make benchmark

# Add to CI/CD pipeline
python simple_benchmark.py
```

The benchmark results help you understand:
1. **Which AWS operations are slowest** - Focus optimization there
2. **Cache effectiveness** - Should see 100x+ speedup with cache
3. **Overall application performance** - Target < 15 seconds total time
4. **Performance trends** - Run regularly to catch regressions