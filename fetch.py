import boto3
import sys
from botocore.exceptions import BotoCoreError, ClientError

def validate_aws_credentials():
    """Validate AWS credentials by making a simple API call."""
    try:
        sts = boto3.client('sts')
        sts.get_caller_identity()
        return True
    except (BotoCoreError, ClientError) as e:
        print(f"\nError: Invalid AWS credentials - {str(e)}")
        print("Please ensure your AWS credentials are properly configured.")
        print("You can configure them using:")
        print("  - AWS CLI: 'aws configure'")
        print("  - Environment variables: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        print("  - IAM role if running on AWS infrastructure\n")
        return False

def is_aurora_instance(engine):
    """Check if the engine indicates an Aurora instance."""
    aurora_engines = ['aurora-mysql', 'aurora-postgresql', 'aurora']
    return engine.lower() in aurora_engines if engine else False

def fetch_rds_instances():
    """Fetch all RDS instances and their key metadata."""
    rds = boto3.client('rds', region_name='ap-south-1')
    instances = []
    try:
        paginator = rds.get_paginator('describe_db_instances')
        for page in paginator.paginate():
            for db in page['DBInstances']:
                engine = db.get('Engine')
                is_aurora = is_aurora_instance(engine)
                
                instances.append({
                    'DBInstanceIdentifier': db.get('DBInstanceIdentifier'),
                    'DBInstanceClass': db.get('DBInstanceClass'),
                    'AllocatedStorage': db.get('AllocatedStorage'),
                    'Iops': db.get('Iops'),
                    'StorageType': db.get('StorageType'),
                    'StorageThroughput': db.get('StorageThroughput'),
                    'Endpoint': db.get('Endpoint', {}).get('Address'),
                    'Engine': engine,
                    'Region': rds.meta.region_name,
                    'IsAurora': is_aurora,
                    'DBClusterIdentifier': db.get('DBClusterIdentifier') if is_aurora else None,
                    'MultiAZ': db.get('MultiAZ', False),
                })
    except (BotoCoreError, ClientError) as e:
        print(f"Error fetching RDS instances: {e}")
    return instances