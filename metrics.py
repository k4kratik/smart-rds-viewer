try:
    import boto3
    _HAS_BOTO = True
except ImportError:
    boto3 = None  # type: ignore
    _HAS_BOTO = False
from datetime import datetime, timedelta

def fetch_storage_metrics(rds_instances):
    """Fetch FreeStorageSpace metric for each RDS instance from CloudWatch."""
    if not _HAS_BOTO:
        print("[WARN] boto3 not installed; returning empty metrics.")
        return {}
    cloudwatch = boto3.client('cloudwatch')
    metrics = {}
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)
    for inst in rds_instances:
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
                # Use the latest datapoint
                metrics[db_id] = sorted(datapoints, key=lambda x: x['Timestamp'])[-1]['Average']
            else:
                metrics[db_id] = None
        except Exception as e:
            print(f"Error fetching metrics for {db_id}: {e}")
            metrics[db_id] = None
    return metrics
