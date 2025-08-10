#!/usr/bin/env python3
"""
Debug script for testing backup and maintenance data fetching.
This script helps identify issues and validate data extraction.
"""

import os
import sys
from rich.console import Console
from rich.table import Table
from rich import box

# Set up environment
os.environ['AWS_PROFILE'] = 'kutumb-mfa'
os.environ['AWS_REGION'] = 'ap-south-1'

console = Console()

def debug_rds_instances():
    """Debug RDS instance fetching"""
    console.print("[bold blue]Step 1: Testing RDS instance fetching...[/bold blue]")
    
    try:
        from fetch import fetch_rds_instances
        instances = fetch_rds_instances()
        
        console.print(f"✅ Found {len(instances)} RDS instances")
        
        if instances:
            # Show sample instance data
            sample = instances[0]
            console.print("\n[bold]Sample instance data:[/bold]")
            for key, value in sample.items():
                console.print(f"  {key}: {value}")
        
        return instances
        
    except Exception as e:
        console.print(f"❌ Error fetching RDS instances: {e}")
        import traceback
        traceback.print_exc()
        return []

def debug_backup_maintenance_data(instances):
    """Debug backup and maintenance data fetching"""
    console.print("\n[bold blue]Step 2: Testing backup and maintenance data fetching...[/bold blue]")
    
    if not instances:
        console.print("❌ No instances to process")
        return {}, {}
    
    try:
        from backup_maintenance import fetch_backup_maintenance_data
        backup_data, maintenance_data = fetch_backup_maintenance_data(instances)
        
        console.print(f"✅ Backup data retrieved for {len(backup_data)} instances")
        console.print(f"✅ Maintenance data retrieved for {len(maintenance_data)} instances")
        
        # Show sample data
        if backup_data:
            instance_name = list(backup_data.keys())[0]
            console.print(f"\n[bold]Sample backup data for '{instance_name}':[/bold]")
            for key, value in backup_data[instance_name].items():
                console.print(f"  {key}: {value}")
        
        if maintenance_data:
            instance_name = list(maintenance_data.keys())[0]
            console.print(f"\n[bold]Sample maintenance data for '{instance_name}':[/bold]")
            for key, value in maintenance_data[instance_name].items():
                console.print(f"  {key}: {value}")
        
        return backup_data, maintenance_data
        
    except Exception as e:
        console.print(f"❌ Error fetching backup/maintenance data: {e}")
        import traceback
        traceback.print_exc()
        return {}, {}

def debug_data_formatting(instances, backup_data, maintenance_data):
    """Debug data formatting functions"""
    console.print("\n[bold blue]Step 3: Testing data formatting...[/bold blue]")
    
    try:
        from backup_maintenance import (
            format_backup_window_display,
            format_maintenance_window_display,
            format_pending_actions_display,
            get_next_maintenance_status
        )
        
        # Test with sample data
        if instances and backup_data and maintenance_data:
            instance = instances[0]
            instance_name = instance['DBInstanceIdentifier']
            
            backup_info = backup_data.get(instance_name, {})
            maintenance_info = maintenance_data.get(instance_name, {})
            
            console.print(f"\n[bold]Formatting test for '{instance_name}':[/bold]")
            
            # Test backup window formatting
            backup_window = backup_info.get('backup_window', 'Not set')
            formatted_backup = format_backup_window_display(backup_window)
            console.print(f"  Backup window: '{backup_window}' → '{formatted_backup}'")
            
            # Test maintenance window formatting
            maintenance_window = maintenance_info.get('maintenance_window', 'Not set')
            formatted_maintenance = format_maintenance_window_display(maintenance_window)
            console.print(f"  Maintenance window: '{maintenance_window}' → '{formatted_maintenance}'")
            
            # Test next maintenance calculation
            next_maintenance = maintenance_info.get('next_maintenance_time')
            formatted_next = get_next_maintenance_status(next_maintenance)
            console.print(f"  Next maintenance: '{next_maintenance}' → '{formatted_next}'")
            
            # Test pending actions formatting
            pending_actions = maintenance_info.get('pending_actions', [])
            formatted_actions = format_pending_actions_display(pending_actions)
            console.print(f"  Pending actions: {len(pending_actions)} actions → '{formatted_actions}'")
            
            console.print("✅ Data formatting tests completed")
        
    except Exception as e:
        console.print(f"❌ Error in data formatting: {e}")
        import traceback
        traceback.print_exc()

def create_debug_table(instances, backup_data, maintenance_data):
    """Create a simple table to visualize the data"""
    console.print("\n[bold blue]Step 4: Creating debug table...[/bold blue]")
    
    try:
        from backup_maintenance import (
            format_backup_window_display,
            format_maintenance_window_display,
            format_pending_actions_display,
            get_next_maintenance_status
        )
        
        table = Table(title="Debug: RDS Backup & Maintenance Data", box=box.SIMPLE_HEAVY)
        
        # Add columns
        table.add_column("Name", justify="left", style="bold")
        table.add_column("Class", justify="left")
        table.add_column("Engine", justify="left")
        table.add_column("Backup Window", justify="left")
        table.add_column("Backup Retention", justify="center")
        table.add_column("Maintenance Window", justify="left")
        table.add_column("Next Maintenance", justify="left")
        table.add_column("Pending Actions", justify="left")
        
        # Add data rows
        for instance in instances:
            name = instance['DBInstanceIdentifier']
            instance_class = instance['DBInstanceClass']
            engine = instance.get('Engine', 'Unknown')
            
            # Get backup and maintenance info
            backup_info = backup_data.get(name, {})
            maintenance_info = maintenance_data.get(name, {})
            
            # Format data
            backup_window = format_backup_window_display(backup_info.get('backup_window', 'Not set'))
            backup_retention = f"{backup_info.get('backup_retention_period', 0)}d" if backup_info.get('backup_retention_period', 0) > 0 else "Disabled"
            maintenance_window = format_maintenance_window_display(maintenance_info.get('maintenance_window', 'Not set'))
            next_maintenance = get_next_maintenance_status(maintenance_info.get('next_maintenance_time'))
            pending_actions = format_pending_actions_display(maintenance_info.get('pending_actions', []))
            
            # Add row
            table.add_row(
                name,
                instance_class,
                engine,
                backup_window,
                backup_retention,
                maintenance_window,
                next_maintenance,
                pending_actions
            )
        
        console.print(table)
        console.print(f"\n✅ Debug table created with {len(instances)} instances")
        
    except Exception as e:
        console.print(f"❌ Error creating debug table: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main debug function"""
    console.print("[bold green]🔍 RDS Backup & Maintenance Debug Script[/bold green]")
    console.print("=" * 60)
    
    # Step 1: Fetch RDS instances
    instances = debug_rds_instances()
    
    if not instances:
        console.print("❌ Cannot continue without RDS instances")
        return
    
    # Step 2: Fetch backup and maintenance data
    backup_data, maintenance_data = debug_backup_maintenance_data(instances)
    
    # Step 3: Test data formatting
    debug_data_formatting(instances, backup_data, maintenance_data)
    
    # Step 4: Create debug table
    create_debug_table(instances, backup_data, maintenance_data)
    
    console.print("\n[bold green]🎉 Debug script completed![/bold green]")
    
    # Summary
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  • RDS Instances: {len(instances)}")
    console.print(f"  • Backup Data: {len(backup_data)} instances")
    console.print(f"  • Maintenance Data: {len(maintenance_data)} instances")
    
    # Show any issues
    issues = []
    if len(backup_data) != len(instances):
        issues.append("Backup data count mismatch")
    if len(maintenance_data) != len(instances):
        issues.append("Maintenance data count mismatch")
    
    if issues:
        console.print(f"\n[bold red]⚠️ Issues found:[/bold red]")
        for issue in issues:
            console.print(f"  • {issue}")
    else:
        console.print(f"\n[bold green]✅ All data extraction working correctly![/bold green]")

if __name__ == "__main__":
    main()
