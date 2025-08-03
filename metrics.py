import boto3
from datetime import datetime, timedelta

def fetch_storage_metrics(rds_instances):
    """Fetch FreeStorageSpace metric for each RDS instance from CloudWatch."""
    cloudwatch = boto3.client('cloudwatch', region_name='ap-south-1')
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