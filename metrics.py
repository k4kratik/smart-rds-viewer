import boto3
from datetime import datetime, timedelta
from fetch import is_aurora_instance

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

def fetch_storage_metrics(rds_instances):
    """Fetch FreeStorageSpace metric for each RDS instance from CloudWatch."""
    cloudwatch = boto3.client('cloudwatch', region_name='ap-south-1')
    metrics = {}
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)
    
    for inst in rds_instances:
        db_id = inst['DBInstanceIdentifier']
        is_aurora = inst.get('IsAurora', False)
        
        try:
            if is_aurora:
                # For Aurora instances, storage is managed at cluster level
                # Aurora uses dynamic storage allocation, so traditional storage metrics don't apply
                cluster_id = inst.get('DBClusterIdentifier')
                if cluster_id:
                    print(f"Aurora instance {db_id} - using cluster-level storage (dynamic)")
                    metrics[db_id] = None  # No traditional storage metrics for Aurora
                else:
                    metrics[db_id] = None
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
                    metrics[db_id] = sorted(datapoints, key=lambda x: x['Timestamp'])[-1]['Average']
                else:
                    metrics[db_id] = None
        except Exception as e:
            print(f"Error fetching metrics for {db_id}: {e}")
            metrics[db_id] = None
    return metrics