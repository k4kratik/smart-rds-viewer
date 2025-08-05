import boto3
import threading
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

# Optimized boto3 configuration
OPTIMIZED_CONFIG = Config(
    max_pool_connections=30,
    retries={'max_attempts': 3, 'mode': 'adaptive'},
    connect_timeout=10,
    read_timeout=30
)

# Thread-local storage for boto3 clients
_local = threading.local()

def get_optimized_rds_client(region='ap-south-1'):
    """Get thread-local optimized RDS client with connection pooling."""
    client_key = f'rds_client_{region}'
    if not hasattr(_local, client_key):
        session = boto3.Session()
        setattr(_local, client_key, session.client('rds', 
                                                  region_name=region,
                                                  config=OPTIMIZED_CONFIG))
    return getattr(_local, client_key)

def fetch_reserved_instances(region='ap-south-1') -> List[Dict]:
    """
    Fetch all Reserved DB Instances from AWS RDS.
    
    Returns:
        List of reserved instance dictionaries with details like:
        - ReservedDBInstanceId
        - DBInstanceClass
        - DBInstanceCount
        - ProductDescription (engine)
        - State (active, payment-pending, retired, etc.)
        - OfferingType (All Upfront, Partial Upfront, No Upfront)
        - RecurringCharges
        - FixedPrice
        - UsagePrice
        - StartTime
        - Duration
    """
    rds = get_optimized_rds_client(region)
    reserved_instances = []
    
    try:
        print(f"[INFO] Fetching Reserved Instances for region {region}...")
        
        # Use paginator to handle large numbers of RIs
        paginator = rds.get_paginator('describe_reserved_db_instances')
        for page in paginator.paginate():
            for ri in page['ReservedDBInstances']:
                # Only include active RIs
                if ri.get('State', '').lower() == 'active':
                    reserved_instances.append({
                        'ReservedDBInstanceId': ri.get('ReservedDBInstanceId'),
                        'DBInstanceClass': ri.get('DBInstanceClass'),
                        'DBInstanceCount': ri.get('DBInstanceCount', 1),
                        'ProductDescription': ri.get('ProductDescription', ''),
                        'Engine': ri.get('ProductDescription', '').lower(),  # Normalize engine name
                        'State': ri.get('State'),
                        'OfferingType': ri.get('OfferingType'),
                        'RecurringCharges': ri.get('RecurringCharges', []),
                        'FixedPrice': ri.get('FixedPrice', 0.0),
                        'UsagePrice': ri.get('UsagePrice', 0.0),
                        'StartTime': ri.get('StartTime'),
                        'Duration': ri.get('Duration', 0),
                        'MultiAZ': ri.get('MultiAZ', False),
                        'Region': region,
                        # Calculate expiry date
                        'ExpiryDate': ri.get('StartTime') + timedelta(seconds=ri.get('Duration', 0)) if ri.get('StartTime') and ri.get('Duration') else None
                    })
        
        print(f"[INFO] Found {len(reserved_instances)} active Reserved Instances")
        return reserved_instances
        
    except (BotoCoreError, ClientError) as e:
        print(f"[ERROR] Failed to fetch Reserved Instances: {e}")
        return []

def normalize_engine_name(engine: str) -> str:
    """
    Normalize engine names for matching between running instances and RIs.
    AWS uses different formats in different APIs.
    """
    if not engine:
        return ""
    
    engine = engine.lower().strip()
    
    # Map common variations
    engine_mapping = {
        'mysql': 'mysql',
        'postgresql': 'postgresql', 
        'postgres': 'postgresql',
        'aurora-mysql': 'aurora mysql',
        'aurora-postgresql': 'aurora postgresql',
        'aurora': 'aurora mysql',  # Default Aurora to MySQL
        'mariadb': 'mariadb',
        'oracle-ee': 'oracle',
        'oracle-se2': 'oracle',
        'sqlserver-ex': 'sql server',
        'sqlserver-web': 'sql server',
        'sqlserver-se': 'sql server',
        'sqlserver-ee': 'sql server',
    }
    
    return engine_mapping.get(engine, engine)

def get_instance_size_weight(instance_class: str) -> float:
    """
    Get the relative size weight for RDS instance size flexibility.
    AWS RDS RIs have size flexibility within the same family.
    
    Returns the weight where nano=0.25, micro=0.5, small=1, medium=2, large=4, etc.
    """
    if not instance_class:
        return 1.0
    
    # Extract size from instance class (e.g., db.r6g.large -> large)
    parts = instance_class.split('.')
    if len(parts) < 3:
        return 1.0
    
    size = parts[2].lower()
    
    # AWS instance size weights for RI flexibility
    size_weights = {
        'nano': 0.25,
        'micro': 0.5,
        'small': 1.0,
        'medium': 2.0,
        'large': 4.0,
        'xlarge': 8.0,
        '2xlarge': 16.0,
        '3xlarge': 24.0,
        '4xlarge': 32.0,
        '6xlarge': 48.0,
        '8xlarge': 64.0,
        '9xlarge': 72.0,
        '10xlarge': 80.0,
        '12xlarge': 96.0,
        '16xlarge': 128.0,
        '18xlarge': 144.0,
        '24xlarge': 192.0,
        '32xlarge': 256.0,
    }
    
    return size_weights.get(size, 1.0)

def get_instance_family(instance_class: str) -> str:
    """
    Extract the instance family from instance class.
    E.g., db.r6g.large -> r6g
    """
    if not instance_class:
        return ""
    
    parts = instance_class.split('.')
    if len(parts) < 2:
        return ""
    
    return parts[1].lower()

def match_reserved_instances(running_instances: List[Dict], reserved_instances: List[Dict]) -> Dict:
    """
    Match running instances to Reserved Instances with AWS RDS size flexibility.
    
    AWS RDS RIs have instance size flexibility within the same family:
    - Same instance family (e.g., r6g, m6g, t4g)
    - Same engine type
    - Same region
    - Same Multi-AZ configuration
    - Size flexibility: smaller RIs can combine to cover larger instances
    
    Returns:
        Dictionary with RI matching information
    """
    matches = []
    fully_covered = []
    partially_covered = []
    uncovered = []
    
    # Convert RIs to a pool of capacity by family/engine/region/multi-az
    ri_pools = {}
    
    for ri in reserved_instances:
        family = get_instance_family(ri['DBInstanceClass'])
        engine = normalize_engine_name(ri['Engine'])
        region = ri['Region']
        multi_az = ri['MultiAZ']
        
        # Create pool key
        pool_key = (family, engine, region, multi_az)
        
        if pool_key not in ri_pools:
            ri_pools[pool_key] = {
                'total_weight': 0.0,
                'remaining_weight': 0.0,
                'ris': []
            }
        
        # Calculate weight contribution of this RI
        ri_weight = get_instance_size_weight(ri['DBInstanceClass'])
        total_ri_weight = ri_weight * ri['DBInstanceCount']
        
        ri_pools[pool_key]['total_weight'] += total_ri_weight
        ri_pools[pool_key]['remaining_weight'] += total_ri_weight
        ri_pools[pool_key]['ris'].append({
            **ri,
            'weight_per_unit': ri_weight,
            'total_weight': total_ri_weight,
            'remaining_weight': total_ri_weight
        })
    
    print(f"[INFO] Created {len(ri_pools)} RI pools for matching")
    for pool_key, pool in ri_pools.items():
        family, engine, region, multi_az = pool_key
        print(f"[INFO] Pool {family}|{engine}|{region}|{'Multi-AZ' if multi_az else 'Single-AZ'}: {pool['total_weight']} weight units")
    
    # Sort instances by weight (largest first) to prioritize high-value instances
    sorted_instances = sorted(running_instances, 
                            key=lambda x: get_instance_size_weight(x.get('DBInstanceClass', '')), 
                            reverse=True)
    
    for instance in sorted_instances:
        instance_class = instance.get('DBInstanceClass', '')
        instance_engine = normalize_engine_name(instance.get('Engine', ''))
        instance_region = instance.get('Region', '')
        instance_multi_az = instance.get('MultiAZ', False)
        instance_id = instance.get('DBInstanceIdentifier', '')
        
        # Calculate instance weight
        instance_weight = get_instance_size_weight(instance_class)
        instance_family = get_instance_family(instance_class)
        
        # Look for matching RI pool
        pool_key = (instance_family, instance_engine, instance_region, instance_multi_az)
        
        if pool_key in ri_pools and ri_pools[pool_key]['remaining_weight'] > 0:
            pool = ri_pools[pool_key]
            
            if pool['remaining_weight'] >= instance_weight:
                # Full coverage
                pool['remaining_weight'] -= instance_weight
                
                # Find which specific RIs to deduct from
                remaining_to_deduct = instance_weight
                matched_ris = []
                
                for ri_data in pool['ris']:
                    if remaining_to_deduct <= 0:
                        break
                    if ri_data['remaining_weight'] <= 0:
                        continue
                    
                    deduction = min(remaining_to_deduct, ri_data['remaining_weight'])
                    ri_data['remaining_weight'] -= deduction
                    remaining_to_deduct -= deduction
                    matched_ris.append((ri_data, deduction))
                
                matches.append((instance, matched_ris, 100))
                fully_covered.append(instance)
                
            elif pool['remaining_weight'] > 0:
                # Partial coverage
                coverage_percent = (pool['remaining_weight'] / instance_weight) * 100
                
                # Use all remaining RI capacity
                matched_ris = []
                for ri_data in pool['ris']:
                    if ri_data['remaining_weight'] > 0:
                        matched_ris.append((ri_data, ri_data['remaining_weight']))
                        ri_data['remaining_weight'] = 0
                
                pool['remaining_weight'] = 0
                matches.append((instance, matched_ris, coverage_percent))
                partially_covered.append(instance)
            else:
                uncovered.append(instance)
        else:
            uncovered.append(instance)
    
    # Calculate RI utilization statistics based on weight usage
    ri_utilization = {}
    unused_ris = []
    
    for pool_key, pool in ri_pools.items():
        for ri_data in pool['ris']:
            ri = {k: v for k, v in ri_data.items() if k not in ['weight_per_unit', 'total_weight', 'remaining_weight']}
            ri_id = ri['ReservedDBInstanceId']
            
            # Calculate utilization based on weight
            total_weight = ri_data['total_weight']
            remaining_weight = ri_data['remaining_weight']
            used_weight = total_weight - remaining_weight
            utilization_percent = (used_weight / total_weight) * 100 if total_weight > 0 else 0
            
            # Convert back to "instance" terms for display
            weight_per_unit = ri_data['weight_per_unit']
            total_capacity = ri['DBInstanceCount']
            remaining_capacity = remaining_weight / weight_per_unit if weight_per_unit > 0 else 0
            used_capacity = total_capacity - remaining_capacity
            
            ri_utilization[ri_id] = {
                'total_capacity': total_capacity,
                'used_capacity': used_capacity,
                'remaining_capacity': remaining_capacity,
                'utilization_percent': utilization_percent,
                'ri_details': ri
            }
            
            if remaining_weight > 0:
                unused_ris.append(ri)
    
    return {
        'matches': matches,
        'fully_covered': fully_covered,
        'partially_covered': partially_covered,
        'uncovered': uncovered,
        'unused_ris': unused_ris,
        'ri_utilization': ri_utilization
    }

def calculate_effective_pricing(pricing_data: Dict, ri_matches: Dict) -> Dict:
    """
    Calculate effective pricing considering Reserved Instance discounts with size flexibility.
    
    Args:
        pricing_data: Original on-demand pricing data
        ri_matches: RI matching results from match_reserved_instances()
    
    Returns:
        Updated pricing data with effective prices considering RI coverage
    """
    effective_pricing = {}
    
    # Create a lookup for RI hourly rates
    ri_hourly_rates = {}
    for ri_id, ri_util in ri_matches['ri_utilization'].items():
        ri = ri_util['ri_details']
        
        # Calculate hourly rate from RI pricing
        # RI pricing = (FixedPrice / duration_hours) + recurring_hourly_charges
        duration_hours = ri['Duration'] / 3600 if ri['Duration'] > 0 else 1
        fixed_hourly = ri['FixedPrice'] / duration_hours if duration_hours > 0 else 0
        
        # Get recurring charges (usually hourly)
        recurring_hourly = 0
        for charge in ri.get('RecurringCharges', []):
            if charge.get('Frequency') == 'Hourly':
                recurring_hourly += charge.get('Amount', 0)
        
        total_hourly_rate = fixed_hourly + recurring_hourly
        ri_hourly_rates[ri_id] = total_hourly_rate
    
    # Process each instance with its matched RIs
    for instance, matched_ris, coverage_percent in ri_matches['matches']:
        instance_id = instance.get('DBInstanceIdentifier')
        region = instance.get('Region')
        engine = instance.get('Engine')
        pricing_key = (instance_id, region, engine)
        
        # Get original pricing
        original_pricing = pricing_data.get(pricing_key)
        if not original_pricing:
            continue
        
        original_instance_price = original_pricing.get('instance', 0)
        
        if coverage_percent >= 100:
            # Full coverage - calculate weighted average of RI rates
            total_weight = sum(weight for _, weight in matched_ris)
            if total_weight > 0:
                weighted_ri_rate = sum(
                    ri_hourly_rates.get(ri_data['ReservedDBInstanceId'], 0) * weight
                    for ri_data, weight in matched_ris
                ) / total_weight
            else:
                weighted_ri_rate = 0
            
            effective_instance_price = weighted_ri_rate
            discount_percent = ((original_instance_price - weighted_ri_rate) / original_instance_price * 100) if original_instance_price > 0 else 0
            
        else:
            # Partial coverage - blend RI and on-demand rates
            coverage_fraction = coverage_percent / 100
            
            # Calculate weighted RI rate for covered portion
            total_weight = sum(weight for _, weight in matched_ris)
            if total_weight > 0:
                weighted_ri_rate = sum(
                    ri_hourly_rates.get(ri_data['ReservedDBInstanceId'], 0) * weight
                    for ri_data, weight in matched_ris
                ) / total_weight
            else:
                weighted_ri_rate = 0
            
            # Blend RI rate (for covered portion) with on-demand rate (for uncovered portion)
            effective_instance_price = (weighted_ri_rate * coverage_fraction + 
                                      original_instance_price * (1 - coverage_fraction))
            discount_percent = ((original_instance_price - effective_instance_price) / original_instance_price * 100) if original_instance_price > 0 else 0
        
        # Get primary RI ID for display (the one contributing most)
        primary_ri_id = None
        if matched_ris:
            primary_ri = max(matched_ris, key=lambda x: x[1])  # RI with highest weight contribution
            primary_ri_id = primary_ri[0]['ReservedDBInstanceId']
        
        # Storage, IOPS, and throughput are typically not covered by RIs (remain at on-demand rates)
        effective_pricing[pricing_key] = {
            'instance': effective_instance_price,
            'storage': original_pricing.get('storage', 0),
            'iops': original_pricing.get('iops', 0), 
            'throughput': original_pricing.get('throughput', 0),
            'total': (effective_instance_price + 
                     original_pricing.get('storage', 0) + 
                     original_pricing.get('iops', 0) + 
                     original_pricing.get('throughput', 0)),
            'original_instance': original_instance_price,
            'ri_discount_percent': discount_percent,
            'ri_covered': True,
            'ri_id': primary_ri_id,
            'coverage_percent': coverage_percent
        }
    
    # Add uncovered instances with original pricing
    for instance in ri_matches['uncovered']:
        instance_id = instance.get('DBInstanceIdentifier')
        region = instance.get('Region')
        engine = instance.get('Engine')
        pricing_key = (instance_id, region, engine)
        
        original_pricing = pricing_data.get(pricing_key)
        if original_pricing:
            effective_pricing[pricing_key] = {
                **original_pricing,
                'original_instance': original_pricing.get('instance', 0),
                'ri_discount_percent': 0,
                'ri_covered': False,
                'ri_id': None,
                'coverage_percent': 0
            }
    
    return effective_pricing