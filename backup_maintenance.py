import boto3
import threading
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Optional, Tuple
from botocore.exceptions import BotoCoreError, ClientError
from fetch import get_optimized_rds_client

# Thread-local storage for boto3 clients
_local = threading.local()

def get_local_timezone():
    """Get the local timezone."""
    try:
        # Try to get the system timezone
        import time
        local_tz = pytz.timezone(time.tzname[0]) if hasattr(time, 'tzname') else None
        if local_tz is None:
            # Fallback to system default
            local_tz = pytz.timezone('UTC')
        return local_tz
    except:
        # If all else fails, use system local timezone
        return datetime.now().astimezone().tzinfo

def convert_utc_time_to_local(time_str: str, local_tz=None) -> str:
    """Convert UTC time string (HH:MM) to local timezone."""
    if not time_str or time_str == 'Not set':
        return time_str
    
    try:
        if local_tz is None:
            local_tz = datetime.now().astimezone().tzinfo
        
        # Parse the time (assuming it's in UTC)
        hour, minute = map(int, time_str.split(':'))
        
        # Create a UTC datetime for today with the given time
        utc_tz = pytz.UTC
        today_utc = datetime.now(utc_tz).replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Convert to local timezone
        local_dt = today_utc.astimezone(local_tz)
        
        return local_dt.strftime('%H:%M')
    except:
        return time_str

def get_timezone_abbreviation(tz=None) -> str:
    """Get timezone abbreviation (e.g., EST, PST, IST)."""
    if tz is None:
        tz = datetime.now().astimezone().tzinfo
    
    try:
        now = datetime.now(tz)
        return now.strftime('%Z')
    except:
        return 'Local'

def fetch_backup_maintenance_data(rds_instances: List[Dict]) -> Tuple[Dict, Dict]:
    """
    Fetch backup and maintenance data for RDS instances.
    
    Returns:
        Tuple of (backup_data, maintenance_data) dictionaries
    """
    if not rds_instances:
        return {}, {}
    
    # Group instances by region
    instances_by_region = {}
    for instance in rds_instances:
        region = instance.get('Region', 'ap-south-1')
        if region not in instances_by_region:
            instances_by_region[region] = []
        instances_by_region[region].append(instance)
    
    backup_data = {}
    maintenance_data = {}
    
    # Process each region
    for region, instances in instances_by_region.items():
        try:
            rds = get_optimized_rds_client(region)
            
            # Get pending maintenance actions for this region
            pending_maintenance = fetch_pending_maintenance_actions(rds)
            
            # Process each instance
            for instance in instances:
                instance_id = instance['DBInstanceIdentifier']
                
                # Extract backup information directly from instance data
                backup_info = {
                    'backup_window': instance.get('PreferredBackupWindow') or 'Not set',
                    'backup_retention_period': instance.get('BackupRetentionPeriod', 0),
                    'backup_target': instance.get('BackupTarget') or 'Unknown',
                    'automated_backup_enabled': (instance.get('BackupRetentionPeriod', 0) or 0) > 0
                }
                backup_data[instance_id] = backup_info
                
                # Extract maintenance information directly from instance data
                maintenance_window = instance.get('PreferredMaintenanceWindow') or 'Not set'
                next_maintenance = calculate_next_maintenance_time(maintenance_window)
                
                # Build instance ARN for pending maintenance lookup
                region = instance.get('Region', 'ap-south-1')
                # For Aurora instances, we need to check both instance and cluster ARNs
                instance_arn = f"arn:aws:rds:{region}:333720180770:db:{instance_id}"
                cluster_id = instance.get('DBClusterIdentifier')
                cluster_arn = f"arn:aws:rds:{region}:333720180770:cluster:{cluster_id}" if cluster_id else None
                
                # Check for pending maintenance actions
                pending_actions = []
                if instance_arn in pending_maintenance:
                    pending_actions.extend(pending_maintenance[instance_arn])
                if cluster_arn and cluster_arn in pending_maintenance:
                    pending_actions.extend(pending_maintenance[cluster_arn])
                
                maintenance_info = {
                    'maintenance_window': maintenance_window,
                    'next_maintenance_time': next_maintenance,
                    'pending_actions': pending_actions,
                    'has_pending_maintenance': len(pending_actions) > 0
                }
                maintenance_data[instance_id] = maintenance_info
                
        except (BotoCoreError, ClientError) as e:
            print(f"Error fetching data for region {region}: {e}")
            continue
    
    return backup_data, maintenance_data

def fetch_pending_maintenance_actions(rds_client) -> Dict:
    """
    Fetch pending maintenance actions for all RDS resources.
    
    Returns:
        Dictionary mapping resource ARN to list of pending actions
    """
    try:
        response = rds_client.describe_pending_maintenance_actions()
        pending_actions = {}
        
        for action_group in response.get('PendingMaintenanceActions', []):
            resource_id = action_group.get('ResourceIdentifier', '')
            actions = []
            
            for action_detail in action_group.get('PendingMaintenanceActionDetails', []):
                action_info = {
                    'action': action_detail.get('Action', 'Unknown'),
                    'description': action_detail.get('Description', 'No description'),
                    'auto_applied_after_date': action_detail.get('AutoAppliedAfterDate'),
                    'forced_apply_date': action_detail.get('ForcedApplyDate'),
                    'opt_in_status': action_detail.get('OptInStatus', 'Unknown')
                }
                actions.append(action_info)
            
            pending_actions[resource_id] = actions
        
        return pending_actions
        
    except (BotoCoreError, ClientError) as e:
        print(f"Error fetching pending maintenance actions: {e}")
        return {}

def calculate_next_maintenance_time(maintenance_window: str) -> Optional[str]:
    """
    Calculate the next maintenance time based on the maintenance window.
    
    Args:
        maintenance_window: String like 'mon:20:30-mon:21:00'
    
    Returns:
        String representation of next maintenance time or None if unable to calculate
    """
    if not maintenance_window or maintenance_window == 'Not set':
        return None
    
    try:
        # Parse maintenance window format: 'day:hh:mm-day:hh:mm'
        # Example: 'mon:20:30-mon:21:00'
        window_parts = maintenance_window.split('-')
        if len(window_parts) != 2:
            return None
        
        start_part = window_parts[0].strip()
        day_time = start_part.split(':')
        if len(day_time) != 3:
            return None
        
        day_name, hour, minute = day_time
        hour = int(hour)
        minute = int(minute)
        
        # Map day names to weekday numbers (Monday=0)
        day_mapping = {
            'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 
            'fri': 4, 'sat': 5, 'sun': 6
        }
        
        if day_name.lower() not in day_mapping:
            return None
        
        target_weekday = day_mapping[day_name.lower()]
        
        # Calculate next occurrence in local timezone
        local_tz = datetime.now().astimezone().tzinfo
        now_local = datetime.now(local_tz)
        
        # Convert UTC maintenance time to local timezone
        utc_tz = pytz.UTC
        today_utc = datetime.now(utc_tz).replace(hour=hour, minute=minute, second=0, microsecond=0)
        maintenance_time_local = today_utc.astimezone(local_tz)
        local_hour = maintenance_time_local.hour
        local_minute = maintenance_time_local.minute
        
        current_weekday = now_local.weekday()
        
        # Calculate days until next maintenance window
        days_ahead = target_weekday - current_weekday
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        # Create target datetime in local timezone
        target_date = now_local + timedelta(days=days_ahead)
        target_datetime = target_date.replace(hour=local_hour, minute=local_minute, second=0, microsecond=0)
        
        # If it's the same day and time hasn't passed yet, use today
        if days_ahead == 7 and now_local.time() < target_datetime.time():
            target_datetime = now_local.replace(hour=local_hour, minute=local_minute, second=0, microsecond=0)
        
        # Convert back to UTC for storage (but this will be displayed in local time)
        target_utc = target_datetime.astimezone(pytz.UTC)
        return target_utc.strftime('%Y-%m-%d %H:%M UTC')
        
    except (ValueError, IndexError) as e:
        return None

def format_backup_window_display(backup_window: str, use_utc: bool = False) -> str:
    """Format backup window for display in UTC or local timezone."""
    if not backup_window or backup_window == 'Not set':
        return 'Not set'
    
    if use_utc:
        # Display in UTC format
        return f"{backup_window} UTC"
    
    try:
        # Convert from HH:MM-HH:MM to local timezone
        start_time, end_time = backup_window.split('-')
        local_tz = datetime.now().astimezone().tzinfo
        tz_abbr = get_timezone_abbreviation(local_tz)
        
        local_start = convert_utc_time_to_local(start_time, local_tz)
        local_end = convert_utc_time_to_local(end_time, local_tz)
        
        return f"{local_start}-{local_end} {tz_abbr}"
    except:
        return backup_window

def format_maintenance_window_display(maintenance_window: str, use_utc: bool = False) -> str:
    """Format maintenance window for display in UTC or local timezone."""
    if not maintenance_window or maintenance_window == 'Not set':
        return 'Not set'
    
    if use_utc:
        # Display in UTC format, capitalize day name
        try:
            window_parts = maintenance_window.split('-')
            start_part = window_parts[0].strip()
            end_part = window_parts[1].strip()
            
            # Extract day and time from start
            start_day_time = start_part.split(':')
            start_day = start_day_time[0].capitalize()
            start_time = f"{start_day_time[1]}:{start_day_time[2]}"
            
            # Extract time from end
            end_day_time = end_part.split(':')
            end_time = f"{end_day_time[1]}:{end_day_time[2]}"
            
            return f"{start_day} {start_time}-{end_time} UTC"
        except:
            return f"{maintenance_window} UTC"
    
    try:
        # Convert from day:hh:mm-day:hh:mm to local timezone
        window_parts = maintenance_window.split('-')
        start_part = window_parts[0].strip()
        end_part = window_parts[1].strip()
        
        # Extract day and time from start
        start_day_time = start_part.split(':')
        start_day = start_day_time[0].capitalize()
        start_time = f"{start_day_time[1]}:{start_day_time[2]}"
        
        # Extract time from end (assume same day)
        end_day_time = end_part.split(':')
        end_time = f"{end_day_time[1]}:{end_day_time[2]}"
        
        # Convert times to local timezone
        local_tz = datetime.now().astimezone().tzinfo
        tz_abbr = get_timezone_abbreviation(local_tz)
        
        local_start = convert_utc_time_to_local(start_time, local_tz)
        local_end = convert_utc_time_to_local(end_time, local_tz)
        
        return f"{start_day} {local_start}-{local_end} {tz_abbr}"
    except:
        return maintenance_window

def format_pending_actions_display(pending_actions: List[Dict]) -> str:
    """Format pending maintenance actions for display."""
    if not pending_actions:
        return "None"
    
    actions = []
    for action in pending_actions:
        action_type = action.get('action', 'Unknown')
        auto_date = action.get('auto_applied_after_date')
        
        if auto_date:
            # Format the date if available
            try:
                if isinstance(auto_date, datetime):
                    date_str = auto_date.strftime('%Y-%m-%d')
                else:
                    date_str = str(auto_date)[:10]  # Take first 10 chars for date
                actions.append(f"{action_type} (auto: {date_str})")
            except:
                actions.append(action_type)
        else:
            actions.append(action_type)
    
    return "; ".join(actions)

def get_next_maintenance_status(next_maintenance: Optional[str]) -> str:
    """Get colored status for next maintenance time."""
    if not next_maintenance:
        return "[dim]Not scheduled[/dim]"
    
    try:
        maintenance_dt = datetime.strptime(next_maintenance, '%Y-%m-%d %H:%M UTC')
        now = datetime.now()
        days_until = (maintenance_dt - now).days
        
        if days_until < 0:
            return "[red]Overdue[/red]"
        elif days_until == 0:
            return "[yellow]Today[/yellow]"
        elif days_until <= 1:
            return f"[yellow]{days_until}d[/yellow]"
        elif days_until <= 7:
            return f"[green]{days_until}d[/green]"
        else:
            return f"{days_until}d"
    except:
        return next_maintenance
