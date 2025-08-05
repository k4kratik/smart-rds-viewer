# Reserved Instance (RI) Feature Implementation

This document explains how the Reserved Instance functionality works in the Smart RDS Viewer, including AWS RDS size flexibility and cost optimization features.

## 📋 Table of Contents

- [Overview](#overview)
- [AWS RDS Reserved Instance Concepts](#aws-rds-reserved-instance-concepts)
- [Implementation Steps](#implementation-steps)
- [Size Flexibility Algorithm](#size-flexibility-algorithm)
- [Matching Logic](#matching-logic)
- [Pricing Calculations](#pricing-calculations)
- [UI Features](#ui-features)
- [Real Example with Data](#real-example-with-data)

## Overview

The RI feature provides comprehensive Reserved Instance analysis including:

- **Automatic RI Discovery**: Fetches all active RIs from your AWS account
- **Size Flexibility Matching**: Handles AWS RDS instance size flexibility within families
- **Coverage Analysis**: Shows which instances are fully/partially covered
- **Cost Optimization**: Calculates actual savings from RI investments
- **Utilization Tracking**: Displays RI utilization rates and unused capacity

## AWS RDS Reserved Instance Concepts

### What are Reserved Instances?

Reserved Instances are a billing discount applied to running instances. You pre-pay for database capacity and get significant cost savings (typically 30-60% off on-demand pricing).

### Size Flexibility

AWS RDS RIs have **instance size flexibility** within the same family:

```
1x db.r6g.4xlarge = 8x db.r6g.large (in terms of RI coverage)
1x db.r6g.2xlarge = 4x db.r6g.large
1x db.r6g.xlarge  = 2x db.r6g.large
```

**Key Requirements for RI Matching:**
- Same instance family (e.g., r6g, m6g, t4g)
- Same database engine (MySQL, PostgreSQL, etc.)
- Same region
- Same Multi-AZ configuration

## Implementation Steps

### Step 1: Fetching Reserved Instance Data

```python
# File: reserved_instances.py - fetch_reserved_instances()

def fetch_reserved_instances(region='ap-south-1') -> List[Dict]:
    """Fetch all active Reserved DB Instances from AWS RDS."""
    
    # Use AWS API to get RI data
    paginator = rds.get_paginator('describe_reserved_db_instances')
    
    for page in paginator.paginate():
        for ri in page['ReservedDBInstances']:
            # Only include active RIs
            if ri.get('State', '').lower() == 'active':
                reserved_instances.append({
                    'ReservedDBInstanceId': ri.get('ReservedDBInstanceId'),
                    'DBInstanceClass': ri.get('DBInstanceClass'),
                    'DBInstanceCount': ri.get('DBInstanceCount', 1),
                    'Engine': ri.get('ProductDescription', '').lower(),
                    'FixedPrice': ri.get('FixedPrice', 0.0),
                    'RecurringCharges': ri.get('RecurringCharges', []),
                    # ... other fields
                })
```

**What this does:**
- Calls AWS API: `describe_reserved_db_instances`
- Filters only "active" RIs (not expired/pending)
- Extracts key information: instance class, count, pricing, etc.

### Step 2: Instance Size Weight System

```python
# File: reserved_instances.py - get_instance_size_weight()

def get_instance_size_weight(instance_class: str) -> float:
    """Calculate relative size weight for RDS instance size flexibility."""
    
    # AWS instance size weights for RI flexibility
    size_weights = {
        'nano': 0.25,
        'micro': 0.5,
        'small': 1.0,
        'medium': 2.0,
        'large': 4.0,        # Base unit
        'xlarge': 8.0,
        '2xlarge': 16.0,
        '3xlarge': 24.0,
        '4xlarge': 32.0,     # 8x larger than 'large'
        '6xlarge': 48.0,
        '8xlarge': 64.0,     # 16x larger than 'large'
        # ... up to 32xlarge
    }
    
    # Extract size: db.r6g.large -> 'large' -> 4.0
    size = instance_class.split('.')[2].lower()
    return size_weights.get(size, 1.0)
```

**This is the KEY to size flexibility:**

```python
# Example:
# RI:       db.r6g.large (weight = 4.0) × 8 units = 32.0 total weight
# Instance: db.r6g.4xlarge (weight = 32.0) × 1 instance
# Match:    32.0 RI weight can cover 32.0 instance weight = 100% coverage!
```

### Step 3: RI Pool Creation

```python
# File: reserved_instances.py - match_reserved_instances()

def match_reserved_instances(running_instances, reserved_instances):
    """Match instances to RIs using AWS size flexibility."""
    
    # Create pools of RI capacity grouped by characteristics
    ri_pools = {}
    
    for ri in reserved_instances:
        family = get_instance_family(ri['DBInstanceClass'])  # e.g., 'r6g'
        engine = normalize_engine_name(ri['Engine'])         # e.g., 'mysql'
        region = ri['Region']                                # e.g., 'ap-south-1'
        multi_az = ri['MultiAZ']                            # e.g., False
        
        # Create pool key
        pool_key = (family, engine, region, multi_az)
        
        # Calculate weight contribution
        ri_weight = get_instance_size_weight(ri['DBInstanceClass'])
        total_ri_weight = ri_weight * ri['DBInstanceCount']
        
        # Add to pool
        ri_pools[pool_key]['total_weight'] += total_ri_weight
        ri_pools[pool_key]['remaining_weight'] += total_ri_weight
```

**Pool Example:**
```
Pool: (r6g, mysql, ap-south-1, Single-AZ)
- db.r6g.large × 8 units  = 32.0 weight
- db.r6g.large × 30 units = 120.0 weight  
Total pool capacity: 152.0 weight units
```

### Step 4: Instance Matching Algorithm

```python
# For each running instance:
for instance in sorted_instances:
    instance_weight = get_instance_size_weight(instance_class)
    instance_family = get_instance_family(instance_class)
    
    # Find matching RI pool
    pool_key = (instance_family, instance_engine, instance_region, instance_multi_az)
    
    if pool_key in ri_pools and ri_pools[pool_key]['remaining_weight'] > 0:
        pool = ri_pools[pool_key]
        
        if pool['remaining_weight'] >= instance_weight:
            # Full coverage
            pool['remaining_weight'] -= instance_weight
            matches.append((instance, matched_ris, 100))
            fully_covered.append(instance)
            
        elif pool['remaining_weight'] > 0:
            # Partial coverage
            coverage_percent = (pool['remaining_weight'] / instance_weight) * 100
            matches.append((instance, matched_ris, coverage_percent))
            partially_covered.append(instance)
    else:
        # No coverage
        uncovered.append(instance)
```

**Matching Logic:**
1. Calculate instance weight (e.g., db.r6g.4xlarge = 32.0)
2. Find matching RI pool (r6g|mysql|ap-south-1|Single-AZ)
3. Check pool capacity:
   - **Enough weight**: 100% coverage, deduct from pool
   - **Some weight**: Partial coverage percentage  
   - **No weight**: 0% coverage (uncovered)

## Size Flexibility Algorithm

### Weight Calculation Examples

| Instance Size | Weight | Example |
|---------------|--------|---------|
| db.r6g.large | 4.0 | Base unit |
| db.r6g.xlarge | 8.0 | 2× large |
| db.r6g.2xlarge | 16.0 | 4× large |
| db.r6g.4xlarge | 32.0 | 8× large |
| db.r6g.8xlarge | 64.0 | 16× large |

### Coverage Examples

```python
# Example 1: Perfect Match
RI_Pool: 8× db.r6g.large = 32.0 weight
Instance: 1× db.r6g.4xlarge = 32.0 weight
Result: 100% coverage

# Example 2: Over-Provisioned
RI_Pool: 30× db.r6g.large = 120.0 weight  
Instance: 1× db.r6g.2xlarge = 16.0 weight
Result: 100% coverage (104.0 weight remaining)

# Example 3: Under-Provisioned  
RI_Pool: 2× db.r6g.large = 8.0 weight
Instance: 1× db.r6g.4xlarge = 32.0 weight
Result: 25% coverage (8.0/32.0 = 0.25)
```

## Pricing Calculations

### RI Hourly Rate Calculation

```python
# Calculate RI hourly cost
duration_hours = ri['Duration'] / 3600  # Convert seconds to hours
fixed_hourly = ri['FixedPrice'] / duration_hours  # Amortize upfront cost

# Add recurring charges (usually hourly)
recurring_hourly = sum(
    charge.get('Amount', 0) 
    for charge in ri.get('RecurringCharges', [])
    if charge.get('Frequency') == 'Hourly'
)

total_hourly_rate = fixed_hourly + recurring_hourly
```

### Effective Price Calculation

```python
# For 100% covered instances:
effective_price = RI_hourly_rate  # Significant discount

# For partially covered instances:
coverage_fraction = coverage_percent / 100
effective_price = (RI_rate × coverage_fraction) + (on_demand_rate × (1 - coverage_fraction))

# Example:
# On-demand: $2.50/hr
# RI rate: $1.20/hr  
# 100% coverage: $1.20/hr (52% savings!)
# 50% coverage: ($1.20×0.5) + ($2.50×0.5) = $1.85/hr (26% savings)
```

### Savings Calculation

```python
# Calculate savings per instance
original_instance_price = on_demand_hourly_rate
effective_instance_price = calculated_with_ri_discount
hourly_savings = original_instance_price - effective_instance_price
monthly_savings = hourly_savings * 24 * 30.42  # Average month
```

## UI Features

### Color-Coded Instance Names

- 🟢 **Green names**: 100% RI covered instances
- 🟡 **Yellow names**: Partially RI covered instances  
- ⚪ **Default color**: No RI coverage

### Implementation

```python
# File: ui.py - get_rows()

# Apply color coding based on RI coverage
if ri_covered:
    if coverage_percent >= 100:
        display_name = f"[green]{base_display_name}[/green]"
    else:
        display_name = f"[yellow]{base_display_name}[/yellow]"
else:
    display_name = base_display_name  # Default color
```

### RI Utilization Table

Press **'u'** to toggle the RI Utilization view showing:

- **RI ID**: Reserved Instance identifier
- **Instance Class**: RI size (e.g., db.r6g.large)
- **Total/Used/Available**: Capacity breakdown
- **Utilization %**: How much of each RI is being used
- **Hourly Rate**: Effective RI cost per hour
- **Expires**: Days until RI expires (color-coded warnings)

### Title Bar Information

```
Amazon RDS Instances (Hourly) - Total: $33.30/hr | RI Savings: $19,014.57/mo | RI Covered: 8✓ 1~ 20✗
```

- **RI Savings**: Total monthly savings from RIs
- **8✓**: 8 instances fully covered
- **1~**: 1 instance partially covered  
- **20✗**: 20 instances uncovered

## Real Example with Data

### Example RI Inventory

```
Reserved Instances:
- db.m6g.large × 16 units = 64.0 weight (mysql, ap-south-1)
- db.r6g.large × 50 units = 200.0 weight (mysql + aurora, ap-south-1)
```

### Example Running Instances

```
webapp-db-1 (db.r6g.2xlarge, aurora mysql) = 16.0 weight needed
user-service-db (db.r6g.2xlarge, mysql) = 16.0 weight needed  
analytics-primary (db.m6g.8xlarge, mysql) = 64.0 weight needed
api-reader-1 (db.m6g.4xlarge, mysql) = 32.0 weight needed
```

### Matching Results

```
✅ webapp-db-1: 16.0 needed ← 200.0 available = 100% covered (GREEN)
✅ user-service-db: 16.0 needed ← 184.0 remaining = 100% covered (GREEN)  
✅ analytics-primary: 64.0 needed ← 64.0 m6g pool = 100% covered (GREEN)
❌ api-reader-1: 32.0 needed ← 0.0 m6g remaining = 0% covered (DEFAULT)
```

### Cost Impact

```
Before RIs (On-Demand): $43,327/month
After RIs (Effective):   $24,313/month  
Monthly Savings:         $19,014/month (44% reduction!)
```

### What You See in UI

- **Green instance names**: Fully covered, paying ~50% less
- **Yellow instance names**: Partially covered, paying blended rates  
- **Default color names**: No coverage, paying full on-demand rates
- **Title shows**: "RI Savings: $19,014.57/mo | RI Covered: 8✓ 1~ 20✗"

## The Magic of Size Flexibility

This is why your AWS console shows 100% RI utilization even though instance sizes don't match exactly:

```
Example RI: 8× db.r6g.large (32.0 total weight)
Covers: 1× db.r6g.4xlarge (32.0 weight) = Perfect match!

Example RI: 30× db.r6g.large (120.0 total weight)  
Covers: Multiple smaller instances totaling ~120.0 weight
```

The Smart RDS Viewer accurately models this AWS behavior to show you:
- **Real RI utilization** (matching AWS console)
- **Which specific instances** are covered  
- **Actual cost savings** from your RI investments
- **Optimization opportunities** for uncovered instances

## Key Files

- `reserved_instances.py`: Core RI logic (fetching, matching, pricing)
- `ui.py`: Visual display and color coding
- `rds_viewer.py`: Integration and orchestration

## Dependencies

- `boto3`: AWS SDK for fetching RI data
- `rich`: Terminal UI library for colors and formatting
- Standard Python libraries for date/time calculations