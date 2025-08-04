import boto3
import threading
from datetime import datetime, timedelta
from fetch import is_aurora_instance
from concurrent.futures import ThreadPoolExecutor, as_completed
from botocore.config import Config

# Optimized boto3 configuration
OPTIMIZED_CONFIG = Config(
    max_pool_connections=30,
    retries={'max_attempts': 3, 'mode': 'adaptive'},
    connect_timeout=10,
    read_timeout=30
)

# Thread-local storage for boto3 clients
_local = threading.local()

def get_optimized_cloudwatch_client(region='ap-south-1'):
    """Get thread-local optimized CloudWatch client with connection pooling."""
    client_key = f'cloudwatch_client_{region}'
    if not hasattr(_local, client_key):
        session = boto3.Session()
        setattr(_local, client_key, session.client('cloudwatch', 
                                                  region_name=region,
                                                  config=OPTIMIZED_CONFIG))
    return getattr(_local, client_key)

def fetch_aurora_cluster_storage(cloudwatch, cluster_id, start_time, end_time):
    """Fetch cluster-level storage metrics for Aurora clusters."""
    try:
        # Try to get VolumeReadIOPs as a proxy for Aurora cluster activity
        # Aurora doesn't have FreeStorageSpace at cluster level, so we'll return None
        # for Aurora instances and handle it in the UI logic
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName='VolumeReadIOPs',
            Dimensions=[{'Name': 'DBClusterIdentifier', 'Value': cluster_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=['Average'],
            Unit='Count/Second',
        )
        datapoints = response.get('Datapoints', [])
        if datapoints:
            # Aurora has dynamic storage, so we can't calculate used percentage
            # Return None to indicate no storage metrics available
            return None
        else:
            return None
    except Exception as e:
        print(f"Error fetching Aurora cluster metrics for {cluster_id}: {e}")
        return None

def fetch_instance_metric(cloudwatch_unused, inst, start_time, end_time):
    """Fetch metric for a single RDS instance."""
    db_id = inst['DBInstanceIdentifier']
    is_aurora = inst.get('IsAurora', False)
    
    # Use optimized client instead of passed client
    cloudwatch = get_optimized_cloudwatch_client('ap-south-1')
    
    try:
        if is_aurora:
            # For Aurora instances, storage is managed at cluster level
            # Aurora uses dynamic storage allocation, so traditional storage metrics don't apply
            cluster_id = inst.get('DBClusterIdentifier')
            if cluster_id:
                print(f"Aurora instance {db_id} - using cluster-level storage (dynamic)")
                return db_id, None  # No traditional storage metrics for Aurora
            else:
                return db_id, None
        else:
            # Traditional RDS instance - fetch FreeStorageSpace
            response = cloudwatch.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='FreeStorageSpace',
                Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average'],
                Unit='Bytes',
            )
            datapoints = response.get('Datapoints', [])
            if datapoints:
                # Use the latest datapoint
                metric_value = sorted(datapoints, key=lambda x: x['Timestamp'])[-1]['Average']
                return db_id, metric_value
            else:
                return db_id, None
    except Exception as e:
        print(f"Error fetching metrics for {db_id}: {e}")
        return db_id, None


def fetch_storage_metrics_batch(rds_instances):
    """Fetch FreeStorageSpace metrics using CloudWatch batch API (get_metric_data)."""
    cloudwatch = get_optimized_cloudwatch_client('ap-south-1')
    metrics = {}
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)
    
    # Separate Aurora and traditional RDS instances
    aurora_instances = []
    traditional_instances = []
    
    for inst in rds_instances:
        if inst.get('IsAurora', False):
            aurora_instances.append(inst)
        else:
            traditional_instances.append(inst)
    
    # Handle Aurora instances (no storage metrics)
    for inst in aurora_instances:
        db_id = inst['DBInstanceIdentifier']
        cluster_id = inst.get('DBClusterIdentifier')
        if cluster_id:
            print(f"Aurora instance {db_id} - using cluster-level storage (dynamic)")
        metrics[db_id] = None
    
    if not traditional_instances:
        return metrics
    
    print(f"[INFO] Fetching metrics for {len(traditional_instances)} traditional RDS instances using batch API...")
    
    # CloudWatch get_metric_data can handle up to 500 metrics per request
    # We'll batch in groups of 100 to be safe
    batch_size = 100
    
    for i in range(0, len(traditional_instances), batch_size):
        batch = traditional_instances[i:i + batch_size]
        
        # Prepare metric data queries for this batch
        metric_data_queries = []
        for idx, inst in enumerate(batch):
            db_id = inst['DBInstanceIdentifier']
            metric_data_queries.append({
                'Id': f'metric_{idx}',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/RDS',
                        'MetricName': 'FreeStorageSpace',
                        'Dimensions': [
                            {'Name': 'DBInstanceIdentifier', 'Value': db_id}
                        ]
                    },
                    'Period': 3600,
                    'Stat': 'Average',
                    'Unit': 'Bytes'
                },
                'ReturnData': True
            })
        
        try:
            # Make batch request
            response = cloudwatch.get_metric_data(
                MetricDataQueries=metric_data_queries,
                StartTime=start_time,
                EndTime=end_time
            )
            
            # Process results
            for idx, inst in enumerate(batch):
                db_id = inst['DBInstanceIdentifier']
                metric_id = f'metric_{idx}'
                
                # Find the corresponding metric result
                metric_result = None
                for result in response.get('MetricDataResults', []):
                    if result['Id'] == metric_id:
                        metric_result = result
                        break
                
                if metric_result and metric_result.get('Values'):
                    # Use the latest value
                    metrics[db_id] = metric_result['Values'][-1]
                else:
                    metrics[db_id] = None
                    
        except Exception as e:
            print(f"Error fetching batch metrics: {e}")
            # Fall back to individual metrics for this batch
            for inst in batch:
                db_id = inst['DBInstanceIdentifier']
                try:
                    response = cloudwatch.get_metric_statistics(
                        Namespace='AWS/RDS',
                        MetricName='FreeStorageSpace',
                        Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_id}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,
                        Statistics=['Average'],
                        Unit='Bytes',
                    )
                    datapoints = response.get('Datapoints', [])
                    if datapoints:
                        metrics[db_id] = sorted(datapoints, key=lambda x: x['Timestamp'])[-1]['Average']
                    else:
                        metrics[db_id] = None
                except Exception as individual_e:
                    print(f"Error fetching metrics for {db_id}: {individual_e}")
                    metrics[db_id] = None
    
    return metrics


def fetch_storage_metrics(rds_instances):
    """Fetch FreeStorageSpace metric for each RDS instance from CloudWatch using optimized batch requests."""
    try:
        # Try the optimized batch approach first
        return fetch_storage_metrics_batch(rds_instances)
    except Exception as e:
        print(f"[WARN] Batch metrics failed, falling back to parallel individual requests: {e}")
        
        # Fallback to the parallel individual approach
        cloudwatch = get_optimized_cloudwatch_client('ap-south-1')
        metrics = {}
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        print(f"[INFO] Fetching metrics for {len(rds_instances)} instances in parallel...")
        
        # Use ThreadPoolExecutor to parallelize CloudWatch API calls
        with ThreadPoolExecutor(max_workers=min(10, len(rds_instances))) as executor:
            # Submit all metric requests simultaneously
            future_to_instance = {
                executor.submit(fetch_instance_metric, cloudwatch, inst, start_time, end_time): inst
                for inst in rds_instances
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_instance):
                inst = future_to_instance[future]
                try:
                    db_id, metric_value = future.result()
                    metrics[db_id] = metric_value
                except Exception as e:
                    db_id = inst['DBInstanceIdentifier']
                    print(f"Error processing metrics for {db_id}: {e}")
                    metrics[db_id] = None
        
        return metrics