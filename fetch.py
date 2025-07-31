try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    _HAS_BOTO = True
except ImportError:
    boto3 = None  # type: ignore
    BotoCoreError = ClientError = Exception  # type: ignore
    _HAS_BOTO = False

def fetch_rds_instances():
    """Fetch all RDS instances and their key metadata."""
    if not _HAS_BOTO:
        print("[WARN] boto3 not installed; returning no RDS instances.")
        return []
    rds = boto3.client('rds')
    instances = []
    try:
        paginator = rds.get_paginator('describe_db_instances')
        for page in paginator.paginate():
            for db in page['DBInstances']:
                instances.append({
                    'DBInstanceIdentifier': db.get('DBInstanceIdentifier'),
                    'DBInstanceClass': db.get('DBInstanceClass'),
                    'AllocatedStorage': db.get('AllocatedStorage'),
                    'Iops': db.get('Iops'),
                    'StorageType': db.get('StorageType'),
                    'StorageThroughput': db.get('StorageThroughput'),
                    'Endpoint': db.get('Endpoint', {}).get('Address'),
                    'Engine': db.get('Engine'),
                    'Region': rds.meta.region_name,
                })
    except (BotoCoreError, ClientError) as e:
        print(f"Error fetching RDS instances: {e}")
    return instances
