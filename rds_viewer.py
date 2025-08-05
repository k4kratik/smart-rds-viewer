import sys
import argparse
from fetch import fetch_rds_instances, validate_aws_credentials
from metrics import fetch_storage_metrics
from pricing import fetch_rds_pricing
from reserved_instances import fetch_reserved_instances, match_reserved_instances, calculate_effective_pricing
from ui import display_rds_table
from rich.progress import Progress, SpinnerColumn, TextColumn

def main():
    parser = argparse.ArgumentParser(description="RDS Viewer - Display RDS instances with metrics and pricing")
    parser.add_argument("--nocache", action="store_true", 
                      help="Force fresh data by clearing pricing cache")
    args = parser.parse_args()

    if not validate_aws_credentials():
        sys.exit(1)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="Fetching RDS metadata...", total=None)
        rds_instances = fetch_rds_instances()
        progress.add_task(description="Fetching CloudWatch metrics...", total=None)
        metrics = fetch_storage_metrics(rds_instances)
        progress.add_task(description="Fetching pricing info...", total=None)
        pricing = fetch_rds_pricing(rds_instances, nocache=args.nocache)
        progress.add_task(description="Fetching Reserved Instances...", total=None)
        reserved_instances = fetch_reserved_instances()
        progress.add_task(description="Calculating RI matches and effective pricing...", total=None)
        ri_matches = match_reserved_instances(rds_instances, reserved_instances)
        effective_pricing = calculate_effective_pricing(pricing, ri_matches)
    display_rds_table(rds_instances, metrics, effective_pricing, ri_matches)

if __name__ == "__main__":
    main()