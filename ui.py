from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich import box
from rich.layout import Layout
from rich.panel import Panel
import time
import readchar
import os
import shutil
from datetime import datetime, timedelta
import re
from fetch import is_aurora_instance
from backup_maintenance import (
    format_backup_window_display, 
    format_maintenance_window_display, 
    format_pending_actions_display,
    get_next_maintenance_status
)

console = Console()

def get_terminal_width():
    """Get current terminal width."""
    try:
        return shutil.get_terminal_size().columns
    except:
        return 120  # Default fallback

def calculate_dynamic_spacing(terminal_width, num_columns):
    """Calculate dynamic spacing and column widths based on terminal width."""
    # Reserve space for borders, padding, and separators
    border_space = 4  # Left and right borders
    separator_space = (num_columns - 1) * 3  # Space between columns
    available_width = terminal_width - border_space - separator_space
    
    # Calculate base padding (1 for narrow, 2 for medium, 3 for wide terminals)
    if terminal_width >= 200:
        padding = 3
    elif terminal_width >= 150:
        padding = 2
    else:
        padding = 1
    
    return padding, available_width

def get_backup_column_widths():
    """Get dynamic column widths for backup view based on terminal size."""
    terminal_width = get_terminal_width()
    padding, available_width = calculate_dynamic_spacing(terminal_width, 9)  # 9 columns in backup view
    
    # Define relative importance and minimum widths for each column
    column_specs = {
        'name': {'min': 16, 'weight': 3, 'max': 30},
        'class': {'min': 10, 'weight': 2, 'max': 16},
        'engine': {'min': 8, 'weight': 1, 'max': 12},
        'storage': {'min': 6, 'weight': 1, 'max': 10},
        'backup_window': {'min': 14, 'weight': 2.5, 'max': 22},
        'retention': {'min': 8, 'weight': 1, 'max': 12},
        'maintenance_window': {'min': 16, 'weight': 2.5, 'max': 24},
        'next': {'min': 6, 'weight': 1, 'max': 12},
        'pending_actions': {'min': 12, 'weight': 3, 'max': 35}
    }
    
    return _calculate_column_widths(column_specs, available_width, padding)

def get_pricing_column_widths(has_ri_savings=False):
    """Get dynamic column widths for pricing view based on terminal size."""
    terminal_width = get_terminal_width()
    num_columns = 12 if has_ri_savings else 11  # Include RI savings column if present
    padding, available_width = calculate_dynamic_spacing(terminal_width, num_columns)
    
    # Define column specifications for pricing view - optimized for narrower terminals
    column_specs = {
        'name': {'min': 8, 'weight': 3.5, 'max': 30},         # Compact but expandable
        'class': {'min': 6, 'weight': 2, 'max': 16},          # db.xxx fits in 6
        'storage': {'min': 4, 'weight': 1.5, 'max': 10},      # 1000+ fits
        'used_pct': {'min': 3, 'weight': 0.8, 'max': 7},      # 99% fits in 3
        'free_gb': {'min': 4, 'weight': 1, 'max': 9},         # 999+ fits
        'iops': {'min': 3, 'weight': 1, 'max': 8},            # 30k fits, higher priority
        'storage_throughput': {'min': 3, 'weight': 0.8, 'max': 7},  # 500/gp2 fits
        'instance_price': {'min': 4, 'weight': 1.3, 'max': 11},
        'storage_price': {'min': 4, 'weight': 1.3, 'max': 10},
        'iops_price': {'min': 5, 'weight': 1.2, 'max': 9},    # Enough for "$0.xx" values
        'throughput_price': {'min': 5, 'weight': 1, 'max': 10},
        'total_price': {'min': 4, 'weight': 2, 'max': 11}     # Important column, higher priority
    }
    
    if has_ri_savings:
        column_specs['ri_savings'] = {'min': 4, 'weight': 1.5, 'max': 12}
    
    return _calculate_column_widths(column_specs, available_width, padding)

def get_ri_utilization_column_widths():
    """Get dynamic column widths for RI utilization view based on terminal size."""
    terminal_width = get_terminal_width()
    padding, available_width = calculate_dynamic_spacing(terminal_width, 11)  # 11 columns in RI view
    
    # Define column specifications for RI utilization view
    column_specs = {
        'ri_id': {'min': 20, 'weight': 3, 'max': 30},
        'instance_class': {'min': 10, 'weight': 2, 'max': 16},
        'engine': {'min': 8, 'weight': 1.5, 'max': 12},
        'multi_az': {'min': 6, 'weight': 1, 'max': 8},
        'total': {'min': 5, 'weight': 1, 'max': 8},
        'used': {'min': 5, 'weight': 1, 'max': 8},
        'available': {'min': 8, 'weight': 1, 'max': 10},
        'utilization': {'min': 10, 'weight': 1.5, 'max': 12},
        'offering_type': {'min': 10, 'weight': 1.5, 'max': 14},
        'hourly_rate': {'min': 8, 'weight': 1.5, 'max': 12},
        'expires': {'min': 8, 'weight': 1.5, 'max': 12}
    }
    
    return _calculate_column_widths(column_specs, available_width, padding)

def _calculate_column_widths(column_specs, available_width, padding):
    """Helper function to calculate column widths based on specifications."""
    # Calculate minimum required width
    min_total = sum(spec['min'] for spec in column_specs.values())
    
    if available_width <= min_total:
        # Use minimum widths if terminal is too narrow
        return {col: spec['min'] for col, spec in column_specs.items()}, padding
    
    # Calculate extra space to distribute
    extra_space = available_width - min_total
    total_weight = sum(spec['weight'] for spec in column_specs.values())
    
    # Distribute extra space proportionally
    widths = {}
    for col, spec in column_specs.items():
        extra_for_col = int((extra_space * spec['weight']) / total_weight)
        final_width = min(spec['min'] + extra_for_col, spec['max'])
        widths[col] = final_width
    
    return widths, padding

def clear_terminal():
    """Clear the terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')

def setup_terminal_for_esc():
    """Set up terminal to handle Esc key with minimal delay."""
    # Note: ESCDELAY setting kept for future Esc key implementation
    os.environ['ESCDELAY'] = '1'

def get_key_simple():
    """Simple key reading - back to basics."""
    try:
        return readchar.readkey()
    except:
        return None

# Consistent shortcut assignment across all views
# Time parsing functions for proper sorting
def parse_backup_window_time(backup_window: str) -> tuple:
    """
    Parse backup window for sorting.
    Returns (start_minutes, end_minutes) where minutes is from midnight.
    
    Examples:
    - "03:30-04:00 PST" -> (210, 240)  # 3.5h and 4h from midnight
    - "Not set" -> (9999, 9999)  # Sort last
    """
    if not backup_window or backup_window in ['Not set', 'Disabled']:
        return (9999, 9999)  # Sort disabled/unset windows last
    
    try:
        # Extract time range: "HH:MM-HH:MM TZ" -> "HH:MM-HH:MM"
        time_part = backup_window.split(' ')[0]  # Remove timezone
        start_time, end_time = time_part.split('-')
        
        def time_to_minutes(time_str):
            hours, minutes = map(int, time_str.split(':'))
            return hours * 60 + minutes
        
        start_minutes = time_to_minutes(start_time)
        end_minutes = time_to_minutes(end_time)
        
        return (start_minutes, end_minutes)
    except:
        return (9999, 9999)  # Sort unparseable entries last

def parse_maintenance_window_time(maintenance_window: str) -> tuple:
    """
    Parse maintenance window for sorting.
    Returns (weekday, start_minutes) for proper chronological sorting.
    
    Examples:
    - "Mon 20:30-21:00 PST" -> (0, 1230)  # Monday at 20:30 (0=Monday)
    - "Sun 02:00-03:00 PST" -> (6, 120)   # Sunday at 02:00 (6=Sunday)
    - "Not set" -> (8, 9999)  # Sort last
    """
    if not maintenance_window or maintenance_window in ['Not set', 'Disabled']:
        return (8, 9999)  # Sort after all real days (Sunday=6, so 8 is after all)
    
    try:
        # Extract day and time: "Day HH:MM-HH:MM TZ" -> "Day HH:MM"
        parts = maintenance_window.split(' ')
        if len(parts) < 2:
            return (8, 9999)
        
        day_name = parts[0].lower()
        time_range = parts[1]
        start_time = time_range.split('-')[0]
        
        # Map day names to weekday numbers (Monday=0)
        day_mapping = {
            'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3,
            'fri': 4, 'sat': 5, 'sun': 6
        }
        
        if day_name not in day_mapping:
            return (8, 9999)
        
        weekday = day_mapping[day_name]
        
        # Convert time to minutes from midnight
        hours, minutes = map(int, start_time.split(':'))
        start_minutes = hours * 60 + minutes
        
        return (weekday, start_minutes)
    except:
        return (8, 9999)

def parse_next_maintenance_time(next_maintenance: str) -> int:
    """
    Parse next maintenance time for sorting.
    Returns priority score where lower numbers sort first.
    
    Examples:
    - "Today" or "Overdue" -> 0 (highest priority)
    - "1d" -> 1 (sort by number of days)
    - "Not scheduled" -> 9999 (lowest priority)
    """
    if not next_maintenance or next_maintenance in ['Not scheduled', 'Not set', 'None']:
        return 9999  # Sort unscheduled last
    
    # Strip Rich color markup like [yellow]Today[/yellow] -> Today
    clean_text = re.sub(r'\[[^\]]*\]', '', next_maintenance)
    next_lower = clean_text.lower().strip()
    
    # Handle immediate maintenance
    if any(phrase in next_lower for phrase in ['due now', 'overdue', 'today', 'immediate']):
        return 0
    
    # Extract number of days/hours from common patterns
    try:
        # "Xd" format (like "1d", "3d", "6d")
        days_short_match = re.search(r'(\d+)d$', next_lower)
        if days_short_match:
            return int(days_short_match.group(1))
        
        # "In X days" or "X days"
        days_match = re.search(r'(?:in\s+)?(\d+)\s+days?', next_lower)
        if days_match:
            return int(days_match.group(1))
        
        # "In X hours" -> convert to fractional days
        hours_match = re.search(r'(?:in\s+)?(\d+)\s+hours?', next_lower)
        if hours_match:
            hours = int(hours_match.group(1))
            return max(0, hours / 24)  # Convert to days (fractional)
        
        # "Tomorrow" 
        if 'tomorrow' in next_lower:
            return 1
        
        # "Next week" or "week"
        if any(phrase in next_lower for phrase in ['next week', 'week']):
            return 7
        
        # "Next month" or "month"
        if any(phrase in next_lower for phrase in ['next month', 'month']):
            return 30
        
    except:
        pass
    
    # If we can't parse it, put it in the middle range
    return 500

def _sort_iops_value(iops_value):
    """
    Sort IOPS values in logical order:
    1. Numeric values (0, 3000, 6000, etc.) - ascending
    2. "gp2" (general purpose baseline) - after numbers
    3. "N/A" (not available) - last
    """
    if iops_value is None or iops_value == "":
        return (2, 0)  # Empty/None values at end of numbers
    elif iops_value == "N/A":
        return (3, 0)  # N/A last
    elif iops_value == "gp2":
        return (2, 1)  # gp2 after numbers but before N/A
    elif isinstance(iops_value, (int, float)):
        return (1, iops_value)  # Numbers first, sorted by value
    else:
        # Try to parse as number
        try:
            return (1, float(iops_value))
        except:
            return (3, 1)  # Unparseable values at end

def _sort_throughput_value(throughput_value):
    """
    Sort throughput values in logical order:
    1. Numeric values (125, 250, 500, etc.) - ascending  
    2. "gp2" (general purpose baseline) - after numbers
    3. "N/A" (not available) - last
    """
    if throughput_value is None or throughput_value == "":
        return (2, 0)  # Empty/None values at end of numbers
    elif throughput_value == "N/A":
        return (3, 0)  # N/A last
    elif throughput_value == "gp2":
        return (2, 1)  # gp2 after numbers but before N/A
    elif isinstance(throughput_value, (int, float)):
        return (1, throughput_value)  # Numbers first, sorted by value
    else:
        # Try to parse as number
        try:
            return (1, float(throughput_value))
        except:
            return (3, 1)  # Unparseable values at end

def _sort_price_value(price_value):
    """
    Sort price values with N/A first (meaning no cost/not applicable):
    1. "N/A" (no cost) - best value, sort first
    2. Numeric values (0.0000, 0.0210, etc.) - ascending by cost
    """
    if price_value is None or price_value == "":
        return (2, float('inf'))  # None/empty at end
    elif price_value == "N/A":
        return (0, 0)  # N/A first (no cost is best)
    elif isinstance(price_value, (int, float)):
        return (1, price_value)  # Numbers second, sorted by value
    else:
        # Try to parse as number (handle $ prefix and other formatting)
        try:
            # Remove common currency symbols and whitespace
            clean_value = str(price_value).replace('$', '').replace(',', '').strip()
            return (1, float(clean_value))
        except:
            return (2, float('inf'))  # Unparseable values at end

def get_column_header_with_sort_indicator(column_name: str, column_key: str, sort_state: dict) -> str:
    """Add visual sorting indicator to column header."""
    if sort_state['key'] == column_key:
        # Column is currently being sorted
        direction_arrow = "↑" if sort_state['ascending'] else "↓"
        if sort_state['ascending']:
            return f"[bold cyan underline]{column_name}[/bold cyan underline] [bright_cyan]{direction_arrow}[/bright_cyan]"
        else:
            return f"[bold magenta underline]{column_name}[/bold magenta underline] [bright_magenta]{direction_arrow}[/bright_magenta]"
    else:
        # Regular column header
        return column_name

def get_column_shortcuts():
    """Get simple number-based shortcuts (1-9) for columns based on position."""
    # No longer needed - we'll use positional numbers instead
    return {}

def display_rds_table(rds_instances, metrics=None, pricing=None, ri_matches=None, backup_data=None, maintenance_data=None):
    
    sort_state = {'key': 'name', 'ascending': True}
    show_help = False
    show_monthly = False  # Toggle between hourly and monthly view
    current_view = 'instances'  # Three views: 'instances', 'ri_utilization', 'backup_maintenance'
    
    def get_columns():
        """Get column definitions based on current view mode."""
        if current_view == 'backup_maintenance':
            columns = [
                {'name': 'Name', 'key': 'name', 'justify': 'left'},
                {'name': 'Class', 'key': 'class', 'justify': 'left'},
                {'name': 'Engine', 'key': 'engine', 'justify': 'left'},
                {'name': 'Storage', 'key': 'storage', 'justify': 'right'},
                {'name': 'Backup Window', 'key': 'backup_window', 'justify': 'left'},
                {'name': 'Retention', 'key': 'backup_retention', 'justify': 'center'},
                {'name': 'Maintenance Window', 'key': 'maintenance_window', 'justify': 'left'},
                {'name': 'Next', 'key': 'next_maintenance', 'justify': 'left'},
                {'name': 'Pending Actions', 'key': 'pending_actions', 'justify': 'left'},
            ]
        else:
            # Default pricing view (for both instances and RI views when showing instances)
            price_unit = "$/mo" if show_monthly else "$/hr"
            columns = [
                {'name': 'Name', 'key': 'name', 'justify': 'left'},
                {'name': 'Class', 'key': 'class', 'justify': 'left'},
                {'name': 'Storage (GB)', 'key': 'storage', 'justify': 'right'},
                {'name': '% Used', 'key': 'used_pct', 'justify': 'right'},
                {'name': 'Free (GiB)', 'key': 'free_gb', 'justify': 'right'},
                {'name': 'IOPS', 'key': 'iops', 'justify': 'right'},
                {'name': 'EBS\nThroughput', 'key': 'storage_throughput', 'justify': 'right'},
                {'name': f'Instance\n({price_unit})', 'key': 'instance_price', 'justify': 'right'},
                {'name': f'Storage\n({price_unit})', 'key': 'storage_price', 'justify': 'right'},
                {'name': f'IOPS\n({price_unit})', 'key': 'iops_price', 'justify': 'right'},
                {'name': f'EBS\nThroughput\n({price_unit})', 'key': 'throughput_price', 'justify': 'right'},
                {'name': f'Total\n({price_unit})', 'key': 'total_price', 'justify': 'right'},
            ]
            
            # Add RI savings column if we have RI data
            if ri_matches:
                columns.append({'name': f'RI Savings\n({price_unit})', 'key': 'ri_savings', 'justify': 'right'})
        
        return columns
    
    def get_shortcuts():
        """Get shortcuts for current view columns: 1-9 then a-z."""
        current_columns = get_columns()
        shortcuts = {}
        
        # Map 1-9 for first 9 columns, then a-z for additional columns
        for i, col in enumerate(current_columns):
            if i < 9:  # First 9 columns use numbers 1-9
                shortcuts[str(i + 1)] = col['key']
            elif i < 35:  # Next 26 columns use letters a-z (9 + 26 = 35 total)
                letter_index = i - 9
                letter = chr(ord('a') + letter_index)  # a, b, c, d, e, f...
                
                # Skip 'm' since it's reserved for Monthly toggle
                if letter == 'm':
                    letter_index += 1
                    if letter_index < 26:  # Make sure we don't go beyond 'z'
                        letter = chr(ord('a') + letter_index)  # Skip to 'n'
                    else:
                        continue  # Skip this column if we're at the end
                
                shortcuts[letter] = col['key']
        
        return shortcuts

    def has_multi_az_instances():
        """Check if any instances are Multi-AZ"""
        return any(inst.get('MultiAZ', False) for inst in rds_instances)

    def get_rows():
        rows = []
        for inst in rds_instances:
            name = inst['DBInstanceIdentifier']
            klass = inst['DBInstanceClass']
            storage = inst['AllocatedStorage']
            iops = inst.get('Iops')
            storage_throughput = inst.get('StorageThroughput')
            engine = inst.get('Engine', '')
            is_aurora = is_aurora_instance(engine)
            
            if current_view == 'backup_maintenance':
                # Backup and maintenance view
                backup_info = backup_data.get(name, {}) if backup_data else {}
                maintenance_info = maintenance_data.get(name, {}) if maintenance_data else {}
                
                # Add multi-AZ indicator for display
                is_multi_az = inst.get('MultiAZ', False)
                base_display_name = f"{name} 👥" if is_multi_az else name
                
                rows.append({
                    'name': base_display_name,
                    'class': klass,
                    'engine': engine,
                    'storage': storage if not is_aurora else "Aurora",
                    'backup_window': format_backup_window_display(backup_info.get('backup_window', 'Not set')),
                    'backup_retention': f"{backup_info.get('backup_retention_period', 0)}d" if backup_info.get('backup_retention_period', 0) > 0 else "Disabled",
                    'maintenance_window': format_maintenance_window_display(maintenance_info.get('maintenance_window', 'Not set')),
                    'next_maintenance': get_next_maintenance_status(maintenance_info.get('next_maintenance_time')),
                    'pending_actions': format_pending_actions_display(maintenance_info.get('pending_actions', [])),
                    'is_aurora': is_aurora,
                })
                continue
            
            # Add multi-AZ indicator for display (keep original name for lookups)
            is_multi_az = inst.get('MultiAZ', False)
            base_display_name = f"{name} 👥" if is_multi_az else name
            
            price_info = pricing.get((name, inst['Region'], inst['Engine']))  # Use instance ID as key
            free = metrics.get(name)  # Use original name for metrics lookup
            
            # Get storage type for gp2 detection
            storage_type = inst.get('StorageType', '').lower()
            
            # Handle Aurora instances differently
            if is_aurora:
                # For Aurora: show "Aurora" for storage, "N/A" for storage-related metrics
                storage_display = "Aurora"
                used_pct = "N/A"
                free_gb = "N/A"
                iops_display = "N/A"
                storage_throughput_display = "N/A"
            else:
                # Traditional RDS instance
                storage_display = storage
                
                # Handle gp2 volumes - IOPS and throughput are not configurable
                if storage_type == 'gp2':
                    iops_display = "gp2"
                    storage_throughput_display = "gp2"
                else:
                    iops_display = iops
                    storage_throughput_display = storage_throughput
                
                if free is not None and storage:
                    used_pct = 100 - (free / (storage * 1024**3) * 100)
                    free_gb = free / (1024**3)  # Convert bytes to GB
                else:
                    used_pct = None
                    free_gb = None

            # Extract price components
            instance_price = None
            storage_price = None
            iops_price = None
            throughput_price = None
            total_price = None
            ri_coverage = None
            ri_savings = None
            original_instance_price = None
            
            if price_info is not None:
                if isinstance(price_info, dict):
                    instance_price = price_info.get('instance')
                    storage_price = price_info.get('storage')
                    iops_price = price_info.get('iops')
                    throughput_price = price_info.get('throughput')
                    total_price = price_info.get('total')
                    
                    # RI-specific fields
                    if 'ri_covered' in price_info:
                        ri_covered = price_info.get('ri_covered', False)
                        coverage_percent = price_info.get('coverage_percent', 0)
                        original_instance_price = price_info.get('original_instance', instance_price)
                        ri_discount_percent = price_info.get('ri_discount_percent', 0)
                        
                        # Format RI coverage display
                        if ri_covered:
                            if coverage_percent >= 100:
                                ri_coverage = "[green]100% ✓[/green]"
                            else:
                                ri_coverage = f"[yellow]{coverage_percent:.0f}%[/yellow]"
                        else:
                            ri_coverage = "[red]0%[/red]"
                        
                        # Calculate savings
                        if original_instance_price and original_instance_price > 0:
                            hourly_savings = original_instance_price - instance_price
                            ri_savings = hourly_savings if hourly_savings > 0 else 0
                        else:
                            ri_savings = 0
                        
                        # Apply color coding to instance name based on RI coverage
                        if ri_covered:
                            if coverage_percent >= 100:
                                display_name = f"[green]{base_display_name}[/green]"
                            else:
                                display_name = f"[yellow]{base_display_name}[/yellow]"
                        else:
                            display_name = base_display_name
                    else:
                        ri_savings = 0
                        display_name = base_display_name
                else:
                    # Handle legacy format where price_info was just the instance price
                    instance_price = price_info
                    total_price = price_info
                    ri_savings = 0
                    display_name = base_display_name
            else:
                # Handle case when price_info is None
                ri_savings = 0
                display_name = base_display_name
            
            # For Multi-AZ instances, double the instance price (AWS charges 2x for Multi-AZ)
            if is_multi_az and instance_price is not None and isinstance(instance_price, (int, float)):
                instance_price = instance_price * 2
                # Recalculate total price if it exists
                if total_price is not None and isinstance(total_price, (int, float)):
                    # Subtract old instance price and add new doubled price
                    total_price = total_price + instance_price - (instance_price / 2)
            
            # For Aurora, set storage-related pricing to "N/A"
            if is_aurora:
                storage_price = "N/A"
                iops_price = "N/A"
                throughput_price = "N/A"
            # For gp2 volumes, IOPS and throughput are included in storage price
            elif storage_type == 'gp2':
                iops_price = "N/A"
                throughput_price = "N/A"

            rows.append({
                'name': display_name,
                'class': klass,
                'storage': storage_display,
                'used_pct': used_pct,
                'free_gb': free_gb,
                'iops': iops_display,
                'storage_throughput': storage_throughput_display,
                'instance_price': instance_price,
                'storage_price': storage_price,
                'iops_price': iops_price,
                'throughput_price': throughput_price,
                'total_price': total_price,
                'ri_savings': ri_savings,
                'is_aurora': is_aurora,
            })
        return rows

    def sort_rows(rows):
        k = sort_state['key']
        ascending = sort_state['ascending']
        
        # Define sort functions for each column type
        sort_funcs = {
            'name': lambda r: r['name'] or '',
            'class': lambda r: r['class'] or '',
            'engine': lambda r: r.get('engine', '') or '',
            'storage': lambda r: 0 if r['storage'] == "Aurora" else (r['storage'] or 0),
            'used_pct': lambda r: -1 if r.get('used_pct') == "N/A" else (r.get('used_pct') if r.get('used_pct') is not None else 0),
            'free_gb': lambda r: -1 if r.get('free_gb') == "N/A" else (r.get('free_gb') if r.get('free_gb') is not None else 0),
            'iops': lambda r: _sort_iops_value(r.get('iops')),
            'storage_throughput': lambda r: _sort_throughput_value(r.get('storage_throughput')),
            
            # Backup view columns with time-aware sorting
            'backup_window': lambda r: parse_backup_window_time(r.get('backup_window', '') or ''),
            'backup_retention': lambda r: r.get('backup_retention', '') or '',
            'maintenance_window': lambda r: parse_maintenance_window_time(r.get('maintenance_window', '') or ''),
            'next_maintenance': lambda r: parse_next_maintenance_time(r.get('next_maintenance', '') or ''),
            'pending_actions': lambda r: r.get('pending_actions', '') or '',

            # Pricing view columns with N/A-first sorting
            'instance_price': lambda r: _sort_price_value(r.get('instance_price')),
            'storage_price': lambda r: _sort_price_value(r.get('storage_price')),
            'iops_price': lambda r: _sort_price_value(r.get('iops_price')),
            'throughput_price': lambda r: _sort_price_value(r.get('throughput_price')),
            'total_price': lambda r: _sort_price_value(r.get('total_price')),
            'ri_savings': lambda r: _sort_price_value(r.get('ri_savings')),
        }
        
        keyfunc = sort_funcs.get(k, lambda r: r['name'] or '')
        return sorted(rows, key=keyfunc, reverse=not ascending)

    def create_help_panel(has_multi_az=False):
        columns = get_columns()
        shortcuts = get_shortcuts()
        
        # Build key mappings: 1-9 then a-z (skipping 'm')
        help_items = []
        for i, col in enumerate(columns):
            if i < 9:  # First 9 columns use numbers 1-9
                key = str(i + 1)
            elif i < 35:  # Additional columns use letters a-z
                letter_index = i - 9
                letter = chr(ord('a') + letter_index)
                
                # Skip 'm' since it's reserved for Monthly toggle
                if letter == 'm':
                    letter_index += 1
                    if letter_index < 26:
                        letter = chr(ord('a') + letter_index)  # Skip to 'n'
                    else:
                        continue  # Skip this column
                
                key = letter
            else:
                continue  # Skip columns beyond 35
            
            # Clean up column name for display
            col_name_clean = col['name'].replace('\n', ' ').strip()
            col_name_clean = col_name_clean.replace('($/hr)', '').replace('($/mo)', '').strip()
            col_name_clean = col_name_clean.replace('EBS Throughput', 'EBS Throughput')
            help_items.append((key, col_name_clean))
        
        # Start building the help text
        help_text = "📋 [bold white]Column Sorting - Press 1-9, then a-z[/bold white]\n\n"
        
        # Arrange in 3-column grid format (similar to the image)
        items_per_row = 3
        for i in range(0, len(help_items), items_per_row):
            row_items = help_items[i:i + items_per_row]
            row_parts = []
            
            for key, name in row_items:
                # Format each item as "key → name" with consistent spacing
                formatted_item = f"[cyan]{key}[/cyan] → {name}"
                row_parts.append(f"{formatted_item:<25}")
            
            help_text += "  " + "  ".join(row_parts) + "\n"
        
        # Add special controls section
        help_text += "\n🎮 [bold white]Navigation & Controls[/bold white]\n\n"
        
        # Navigation controls
        help_text += f"  [cyan]←/→[/cyan] → Cycle Views{'':<12}[cyan]Tab[/cyan] → Cycle Views{'':<10}[cyan]Shift+Tab[/cyan] → Cycle Back\n"
        
        # View switching (uppercase to avoid conflicts)
        help_text += f"  [cyan]SHIFT+V[/cyan] → Pricing View{'':<8}[cyan]SHIFT+B[/cyan] → Backup View{'':<8}"
        if ri_matches:
            help_text += "[cyan]SHIFT+R[/cyan] → RI View\n"
        else:
            help_text += "\n"
        
        # Other controls
        help_text += f"  [cyan]?[/cyan] → Help{'':<20}[cyan]m[/cyan] → Monthly/Hourly{'':<12}[cyan]q[/cyan] → Quit\n"
        
        # Visual indicators section
        if ri_matches or has_multi_az:
            help_text += "\n🎨 [bold white]Visual Indicators[/bold white]\n"
            if ri_matches:
                help_text += "  Instance names: [green]Green=100% RI[/green] [yellow]Yellow=Partial RI[/yellow]\n"
            if has_multi_az:
                help_text += "  👥 = Multi-AZ instances (2x pricing)\n"
        
        help_text += "\n[dim]Press any letter to sort by that column, [cyan]?[/cyan] to close this help.[/dim]"
        
        return Panel(help_text, title="💡 Help & Shortcuts - Press [cyan]?[/cyan] to close", 
                    border_style="bright_blue", expand=True, padding=(1, 2))

    def render_table(has_multi_az=False, blur=False):
        # Get dynamic spacing based on terminal width
        if current_view == 'backup_maintenance':
            widths, dynamic_padding = get_backup_column_widths()
            padding = (0, dynamic_padding)
        else:
            # Pricing view - also use dynamic spacing
            has_ri_savings = ri_matches and any(ri_matches.values())
            widths, dynamic_padding = get_pricing_column_widths(has_ri_savings)
            padding = (0, dynamic_padding)
        
        table = Table(title="Amazon RDS Instances", box=box.SIMPLE_HEAVY, padding=padding)
        
        # Add columns dynamically with optimized widths and sorting indicators
        columns = get_columns()
        for col in columns:
            # Get header with sort indicator
            header_text = get_column_header_with_sort_indicator(col['name'], col['key'], sort_state)
            
            if current_view == 'backup_maintenance':
                # Backup & Maintenance view - dynamic column widths based on terminal size
                width_key_map = {
                    'name': 'name',
                    'class': 'class', 
                    'engine': 'engine',
                    'storage': 'storage',
                    'backup_window': 'backup_window',
                    'backup_retention': 'retention',
                    'maintenance_window': 'maintenance_window',
                    'next_maintenance': 'next',
                    'pending_actions': 'pending_actions'
                }
                
                width_key = width_key_map.get(col['key'])
                if width_key and width_key in widths:
                    width = widths[width_key]
                    style = "bold" if col['key'] == 'name' else None
                    no_wrap = col['key'] != 'pending_actions'  # Allow wrapping only for pending actions
                    table.add_column(header_text, justify=col['justify'], style=style, 
                                   width=width, no_wrap=no_wrap)
                else:
                    table.add_column(header_text, justify=col['justify'])
            else:
                # Pricing view - use dynamic column widths
                pricing_width_key_map = {
                    'name': 'name',
                    'class': 'class',
                    'storage': 'storage',
                    'used_pct': 'used_pct',
                    'free_gb': 'free_gb',
                    'iops': 'iops',
                    'storage_throughput': 'storage_throughput',
                    'instance_price': 'instance_price',
                    'storage_price': 'storage_price',
                    'iops_price': 'iops_price',
                    'throughput_price': 'throughput_price',
                    'total_price': 'total_price',
                    'ri_savings': 'ri_savings'
                }
                
                width_key = pricing_width_key_map.get(col['key'])
                if width_key and width_key in widths:
                    width = widths[width_key]
                    style = "bold" if col['key'] == 'name' else None
                    # Allow header wrapping for multi-line headers
                    no_wrap = col['key'] not in ['storage', 'used_pct', 'free_gb', 'iops', 'storage_throughput', 'instance_price', 'storage_price', 'iops_price', 'throughput_price', 'total_price', 'ri_savings']
                    table.add_column(header_text, justify=col['justify'], style=style, 
                                   width=width, no_wrap=no_wrap)
                else:
                    table.add_column(header_text, justify=col['justify'], style="bold" if col['key'] == 'name' else None)
        
        rows = sort_rows(get_rows())
        for row in rows:
            is_aurora = row.get('is_aurora', False)
            
            # Initialize display variables
            used_pct_display = None
            free_gb_display = None
            iops_display = None
            throughput_display = None
            storage_price_display = None
            iops_price_display = None
            throughput_price_display = None
            instance_price_display = None
            total_price_display = None
            ri_savings_display = None
            
            if current_view == 'backup_maintenance':
                # For backup view, we don't need pricing calculations
                pass
            else:
                # Handle % Used column - Color only if >= 80% and not Aurora
                if row.get('used_pct') == "N/A":
                    used_pct_display = "N/A"
                elif row.get('used_pct') is not None and row['used_pct'] >= 80:
                    used_pct_display = f"[red]{row['used_pct']:.1f}%[/red]"
                else:
                    used_pct_display = f"{row['used_pct']:.1f}%" if row.get('used_pct') is not None else "?"
                
                # Handle Free (GiB) column
                if row.get('free_gb') == "N/A":
                    free_gb_display = "N/A"
                else:
                    free_gb_display = f"{row['free_gb']:.1f}" if row.get('free_gb') is not None else "?"
                
                # Handle IOPS and Storage Throughput
                if row.get('iops') == "N/A":
                    iops_display = "N/A"
                elif row.get('iops') == "gp2":
                    iops_display = "gp2"
                elif row.get('iops') is not None:
                    iops_display = str(row['iops'])
                else:
                    iops_display = "-"
                    
                if row.get('storage_throughput') == "N/A":
                    throughput_display = "N/A"
                elif row.get('storage_throughput') == "gp2":
                    throughput_display = "gp2"
                elif row.get('storage_throughput') is not None:
                    throughput_display = str(row['storage_throughput'])
                else:
                    throughput_display = "-"
                
                # Handle pricing columns with monthly conversion
                price_multiplier = 24 * 30.42 if show_monthly else 1  # Convert hourly to monthly
                price_precision = 2 if show_monthly else 4  # Use 2 decimal places for monthly, 4 for hourly
                
                # Format pricing values
                def format_price(price_value, label_value):
                    if label_value == "N/A":
                        return "N/A"
                    elif price_value is not None:
                        adjusted_price = price_value * price_multiplier
                        # Only round actual zero values to clean up display of 0.0000
                        if adjusted_price == 0.0:
                            return "$0"
                        return f"${adjusted_price:.{price_precision}f}"
                    else:
                        return "?"
                
                # Helper function for clean price formatting (also used in totals)
                def format_total_price(amount, precision=None):
                    if precision is None:
                        precision = price_precision
                    # Only round actual zero values to clean up display of 0.0000
                    if amount == 0.0:
                        return "$0"
                    return f"${amount:.{precision}f}"
                
                storage_price_display = format_price(row.get('storage_price'), row.get('storage_price'))
                iops_price_display = format_price(row.get('iops_price'), row.get('iops_price'))
                throughput_price_display = format_price(row.get('throughput_price'), row.get('throughput_price'))
                instance_price_display = format_price(row.get('instance_price'), row.get('instance_price'))
                total_price_display = format_price(row.get('total_price'), row.get('total_price'))
                ri_savings_display = format_price(row.get('ri_savings'), row.get('ri_savings')) if row.get('ri_savings') is not None else None
            
            # Build row data dynamically based on columns
            row_data = []
            for col in columns:
                if col['key'] == 'name':
                    row_data.append(str(row['name']))
                elif col['key'] == 'class':
                    row_data.append(str(row['class']))
                elif col['key'] == 'engine':
                    row_data.append(str(row.get('engine', '')))
                elif col['key'] == 'storage':
                    row_data.append(str(row['storage']))
                elif col['key'] == 'backup_window':
                    row_data.append(str(row.get('backup_window', 'Not set')))
                elif col['key'] == 'backup_retention':
                    row_data.append(str(row.get('backup_retention', 'Disabled')))
                elif col['key'] == 'maintenance_window':
                    row_data.append(str(row.get('maintenance_window', 'Not set')))
                elif col['key'] == 'next_maintenance':
                    row_data.append(str(row.get('next_maintenance', 'Not scheduled')))
                elif col['key'] == 'pending_actions':
                    row_data.append(str(row.get('pending_actions', 'None')))
                elif col['key'] == 'used_pct':
                    row_data.append(used_pct_display)
                elif col['key'] == 'free_gb':
                    row_data.append(free_gb_display)
                elif col['key'] == 'iops':
                    row_data.append(iops_display)
                elif col['key'] == 'storage_throughput':
                    row_data.append(throughput_display)
                elif col['key'] == 'instance_price':
                    row_data.append(instance_price_display)
                elif col['key'] == 'storage_price':
                    row_data.append(storage_price_display)
                elif col['key'] == 'iops_price':
                    row_data.append(iops_price_display)
                elif col['key'] == 'throughput_price':
                    row_data.append(throughput_price_display)
                elif col['key'] == 'total_price':
                    row_data.append(total_price_display)
                elif col['key'] == 'ri_savings':
                    row_data.append(ri_savings_display if ri_savings_display else '[dim]-[/dim]')
            
            table.add_row(*row_data)
        
        # Calculate totals for pricing columns (only for pricing view)
        total_instance_price = 0
        total_storage_price = 0
        total_iops_price = 0
        total_throughput_price = 0
        total_overall_price = 0
        total_ri_savings = 0
        instance_count = len(rows)
        
        if current_view != 'backup_maintenance':
            for row in rows:
                # Sum instance pricing (skip "N/A" values)
                if row.get('instance_price') is not None and isinstance(row.get('instance_price'), (int, float)):
                    total_instance_price += row['instance_price']
                    
                # Sum storage pricing (skip "N/A" values)
                if (row.get('storage_price') != "N/A" and row.get('storage_price') is not None and 
                    isinstance(row.get('storage_price'), (int, float))):
                    total_storage_price += row['storage_price']
                    
                # Sum IOPS pricing (skip "N/A" values)
                if (row.get('iops_price') != "N/A" and row.get('iops_price') is not None and 
                    isinstance(row.get('iops_price'), (int, float))):
                    total_iops_price += row['iops_price']
                    
                # Sum throughput pricing (skip "N/A" values)
                if (row.get('throughput_price') != "N/A" and row.get('throughput_price') is not None and 
                    isinstance(row.get('throughput_price'), (int, float))):
                    total_throughput_price += row['throughput_price']
                    
                # Sum total pricing (skip "N/A" values)
                if row.get('total_price') is not None and isinstance(row.get('total_price'), (int, float)):
                    total_overall_price += row['total_price']
                    
                # Sum RI savings
                if row.get('ri_savings') is not None and isinstance(row.get('ri_savings'), (int, float)):
                    total_ri_savings += row['ri_savings']
        
        # Add divider and totals row only for pricing view
        if current_view != 'backup_maintenance':
            columns = get_columns()
            divider_row = ["─" * 20] + ["─" * 15] * (len(columns) - 1)
            table.add_row(*divider_row, style="dim")
            
            # Add totals row with monthly conversion
            price_multiplier = 24 * 30.42 if show_monthly else 1
            price_precision = 2 if show_monthly else 4
            
            # Build totals row dynamically based on columns
            total_row = []
            for col in columns:
                if col['key'] == 'name':
                    total_row.append(f"[bold]TOTAL ({instance_count} instances)[/bold]")
                elif col['key'] in ['class', 'storage', 'used_pct', 'free_gb', 'iops', 'storage_throughput']:
                    total_row.append("")
                elif col['key'] == 'instance_price':
                    total_row.append(f"[bold]${total_instance_price * price_multiplier:.{price_precision}f}[/bold]")
                elif col['key'] == 'storage_price':
                    total_row.append(f"[bold]${total_storage_price * price_multiplier:.{price_precision}f}[/bold]")
                elif col['key'] == 'iops_price':
                    total_row.append(f"[bold]${total_iops_price * price_multiplier:.{price_precision}f}[/bold]")
                elif col['key'] == 'throughput_price':
                    total_row.append(f"[bold]${total_throughput_price * price_multiplier:.{price_precision}f}[/bold]")
                elif col['key'] == 'total_price':
                    total_row.append(f"[bold]${total_overall_price * price_multiplier:.{price_precision}f}[/bold]")
                elif col['key'] == 'ri_savings':
                    total_row.append(f"[bold green]${total_ri_savings * price_multiplier:.{price_precision}f}[/bold green]")
            
            # Only add TOTAL row in hourly view
            if not show_monthly:
                table.add_row(*total_row, style="bold cyan")
        
        # Add monthly estimate row in pricing mode (always visible)
        if current_view != 'backup_maintenance':
            monthly_total = total_overall_price * 24 * 30.42  # Average month
            monthly_ri_savings = total_ri_savings * 24 * 30.42
            
            # Build monthly row dynamically based on columns
            monthly_row = []
            for col in columns:
                if col['key'] == 'name':
                    monthly_row.append(f"[bold magenta]📅 Monthly Estimate[/bold magenta]")
                elif col['key'] in ['class', 'storage', 'used_pct', 'free_gb', 'iops', 'storage_throughput']:
                    monthly_row.append("")
                elif col['key'] == 'instance_price':
                    monthly_row.append(f"[bold magenta]${total_instance_price * 24 * 30.42:.2f}[/bold magenta]")
                elif col['key'] == 'storage_price':
                    monthly_row.append(f"[bold magenta]${total_storage_price * 24 * 30.42:.2f}[/bold magenta]")
                elif col['key'] == 'iops_price':
                    monthly_row.append(f"[bold magenta]${total_iops_price * 24 * 30.42:.2f}[/bold magenta]")
                elif col['key'] == 'throughput_price':
                    monthly_row.append(f"[bold magenta]${total_throughput_price * 24 * 30.42:.2f}[/bold magenta]")
                elif col['key'] == 'total_price':
                    monthly_row.append(f"[bold bright_magenta]${monthly_total:.2f}[/bold bright_magenta]")
                elif col['key'] == 'ri_savings':
                    monthly_row.append(f"[bold bright_magenta]${monthly_ri_savings:.2f}[/bold bright_magenta]")
            
            table.add_row(*monthly_row, style="bold magenta")
        
        # Add multi-AZ explanation note only if there are Multi-AZ instances
        if has_multi_az:
            # Build note row dynamically based on columns
            note_row = []
            for i, col in enumerate(columns):
                if i == 0:  # First column gets the note
                    note_row.append(f"[dim]👥 = Multi-AZ (2x pricing)[/dim]")
                else:
                    note_row.append("")
            table.add_row(*note_row, style="dim")
        
        # Update table title based on current view mode
        if current_view == 'backup_maintenance':
            table.title = f"Amazon RDS Instances - Backup & Maintenance View ({instance_count} instances)"
        else:
            pricing_view_mode = "Monthly" if show_monthly else "Hourly"
            
            # Add RI information to title if available
            ri_info = ""
            if ri_matches:
                fully_covered_count = len(ri_matches.get('fully_covered', []))
                partially_covered_count = len(ri_matches.get('partially_covered', []))
                uncovered_count = len(ri_matches.get('uncovered', []))
                total_savings_monthly = total_ri_savings * 24 * 30.42 if total_ri_savings > 0 else 0
                
                if total_savings_monthly > 0:
                    ri_info = f" | RI Savings: ${total_savings_monthly:.2f}/mo | RI Covered: {fully_covered_count}✓ {partially_covered_count}~ {uncovered_count}✗"
                else:
                    ri_info = f" | RI Coverage: {fully_covered_count}✓ {partially_covered_count}~ {uncovered_count}✗"
            
            if show_monthly:
                total_display = total_overall_price * 24 * 30.42
                daily_total = total_overall_price * 24
                table.title = f"Amazon RDS Instances ({pricing_view_mode}) - Total: ${total_display:.2f}/mo | Daily: ${daily_total:.2f}/day ({instance_count} instances){ri_info}"
            else:
                daily_total = total_overall_price * 24
                monthly_total = total_overall_price * 24 * 30.42
                table.title = f"Amazon RDS Instances ({pricing_view_mode}) - Total: ${total_overall_price:.4f}/hr | Daily: ${daily_total:.2f}/day | Monthly: ${monthly_total:.2f}/mo ({instance_count} instances){ri_info}"
        
        # Apply blur effect when help is shown
        if blur:
            # Create strong blur effect with multiple layers
            # Layer 1: Dim the table content heavily
            blurred_table = Panel(
                table, 
                style="dim bold",  # Double styling for stronger effect
                border_style="dim",
                padding=(0, 0)
            )
            
            # Layer 2: Add translucent overlay panel for stronger blur
            return Panel(
                blurred_table,
                style="on grey11 dim",  # Dark background overlay with dim
                border_style="bright_black", 
                padding=(0, 0)
            )
        
        return table

    def create_backup_maintenance_table(blur=False):
        """Create a table showing backup and maintenance information."""
        # Get dynamic widths and padding based on terminal size
        widths, dynamic_padding = get_backup_column_widths()
        table = Table(title="Amazon RDS Instances - Backup & Maintenance", box=box.SIMPLE_HEAVY, padding=(0, dynamic_padding))
        
        # Add columns with dynamic widths and sorting indicators
        columns = [
            {'name': 'Name', 'key': 'name', 'justify': 'left', 'style': 'bold', 'width_key': 'name'},
            {'name': 'Class', 'key': 'class', 'justify': 'left', 'width_key': 'class'},
            {'name': 'Engine', 'key': 'engine', 'justify': 'left', 'width_key': 'engine'},
            {'name': 'Storage', 'key': 'storage', 'justify': 'right', 'width_key': 'storage'},
            {'name': 'Backup Window', 'key': 'backup_window', 'justify': 'left', 'width_key': 'backup_window'},
            {'name': 'Retention', 'key': 'backup_retention', 'justify': 'center', 'width_key': 'retention'},
            {'name': 'Maintenance Window', 'key': 'maintenance_window', 'justify': 'left', 'width_key': 'maintenance_window'},
            {'name': 'Next', 'key': 'next_maintenance', 'justify': 'left', 'width_key': 'next'},
            {'name': 'Pending Actions', 'key': 'pending_actions', 'justify': 'left', 'width_key': 'pending_actions'}
        ]
        
        for col in columns:
            header_text = get_column_header_with_sort_indicator(col['name'], col['key'], sort_state)
            style = col.get('style', None)
            no_wrap = col['key'] != 'pending_actions'  # Allow wrapping only for pending actions
            table.add_column(header_text, justify=col['justify'], style=style, 
                           width=widths[col['width_key']], no_wrap=no_wrap)
        
        # Get sorted rows for backup view
        rows = []
        for inst in rds_instances:
            name = inst['DBInstanceIdentifier']
            klass = inst['DBInstanceClass']
            storage = inst['AllocatedStorage']
            engine = inst.get('Engine', '')
            is_aurora = is_aurora_instance(engine)
            
            # Backup and maintenance data
            backup_info = backup_data.get(name, {}) if backup_data else {}
            maintenance_info = maintenance_data.get(name, {}) if maintenance_data else {}
            
            # Add multi-AZ indicator for display
            is_multi_az = inst.get('MultiAZ', False)
            base_display_name = f"{name} 👥" if is_multi_az else name
            
            rows.append({
                'name': base_display_name,
                'class': klass,
                'engine': engine,
                'storage': storage if not is_aurora else "Aurora",
                'backup_window': format_backup_window_display(backup_info.get('backup_window', 'Not set')),
                'backup_retention': f"{backup_info.get('backup_retention_period', 0)}d" if backup_info.get('backup_retention_period', 0) > 0 else "Disabled",
                'maintenance_window': format_maintenance_window_display(maintenance_info.get('maintenance_window', 'Not set')),
                'next_maintenance': get_next_maintenance_status(maintenance_info.get('next_maintenance_time')),
                'pending_actions': format_pending_actions_display(maintenance_info.get('pending_actions', [])),
                'is_aurora': is_aurora,
            })
        
        # Apply current sort state (same as other views)
        rows = sort_rows(rows)
        
        # Add rows to table
        for row in rows:
            table.add_row(
                row['name'],
                row['class'],
                row['engine'],
                str(row['storage']),
                row['backup_window'],
                row['backup_retention'],
                row['maintenance_window'],
                row['next_maintenance'],
                row['pending_actions']
            )
        
        # Update title with instance count
        table.title = f"Amazon RDS Instances - Backup & Maintenance ({len(rows)} instances)"
        
        # Apply blur effect when help is shown
        if blur:
            blurred_table = Panel(
                table, 
                style="dim bold",
                border_style="dim",
                padding=(0, 0)
            )
            return Panel(
                blurred_table,
                style="on grey11 dim",
                border_style="bright_black", 
                padding=(0, 0)
            )
        
        return table

    def create_ri_utilization_table(blur=False):
        """Create a table showing Reserved Instance utilization."""
        if not ri_matches or not ri_matches.get('ri_utilization'):
            # Create empty table with message
            table = Table(title="Reserved Instance Utilization - No RIs found", box=box.SIMPLE_HEAVY)
            table.add_column("Message", justify="center", style="dim")
            table.add_row("No Reserved Instances found in this region.")
            
            # Apply blur effect when help is shown
            if blur:
                # Create strong blur effect with multiple layers
                blurred_table = Panel(
                    table, 
                    style="dim bold",
                    border_style="dim",
                    padding=(0, 0)
                )
                return Panel(
                    blurred_table,
                    style="on grey11 dim",
                    border_style="bright_black", 
                    padding=(0, 0)
                )
            return table
        
        # Get dynamic widths and padding based on terminal size 
        widths, dynamic_padding = get_ri_utilization_column_widths()
        
        table = Table(title="Reserved Instance Utilization", box=box.SIMPLE_HEAVY, padding=(0, dynamic_padding))
        
        # Add columns with dynamic widths and sorting indicators
        ri_columns = [
            {'name': 'RI ID', 'key': 'ri_id', 'justify': 'left', 'style': 'bold', 'width_key': 'ri_id'},
            {'name': 'Instance Class', 'key': 'instance_class', 'justify': 'left', 'width_key': 'instance_class'},
            {'name': 'Engine', 'key': 'engine', 'justify': 'left', 'width_key': 'engine'},
            {'name': 'Multi-AZ', 'key': 'multi_az', 'justify': 'center', 'width_key': 'multi_az'},
            {'name': 'Total', 'key': 'total', 'justify': 'center', 'width_key': 'total'},
            {'name': 'Used', 'key': 'used', 'justify': 'center', 'width_key': 'used'},
            {'name': 'Available', 'key': 'available', 'justify': 'center', 'width_key': 'available'},
            {'name': 'Utilization', 'key': 'utilization', 'justify': 'center', 'width_key': 'utilization'},
            {'name': 'Offering Type', 'key': 'offering_type', 'justify': 'left', 'width_key': 'offering_type'},
            {'name': 'Hourly Rate', 'key': 'hourly_rate', 'justify': 'right', 'width_key': 'hourly_rate'},
            {'name': 'Expires', 'key': 'expires', 'justify': 'left', 'width_key': 'expires'}
        ]
        
        for col in ri_columns:
            header_text = get_column_header_with_sort_indicator(col['name'], col['key'], sort_state)
            style = col.get('style', None)
            table.add_column(header_text, justify=col['justify'], style=style, width=widths[col['width_key']])
        
        total_capacity = 0
        total_used = 0
        total_available = 0
        
        # Sort RIs by utilization (highest first)
        sorted_ris = sorted(ri_matches['ri_utilization'].items(), 
                          key=lambda x: x[1]['utilization_percent'], reverse=True)
        
        for ri_id, utilization in sorted_ris:
            ri_details = utilization['ri_details']
            
            # Calculate hourly rate
            duration_hours = ri_details['Duration'] / 3600 if ri_details['Duration'] > 0 else 1
            fixed_hourly = ri_details['FixedPrice'] / duration_hours if duration_hours > 0 else 0
            recurring_hourly = sum(charge.get('Amount', 0) for charge in ri_details.get('RecurringCharges', []) 
                                 if charge.get('Frequency') == 'Hourly')
            total_hourly_rate = fixed_hourly + recurring_hourly
            
            # Format expiry date
            expiry = ri_details.get('ExpiryDate')
            if expiry:
                # Handle timezone-aware vs timezone-naive datetime comparison
                try:
                    if expiry.tzinfo is not None:
                        # expiry is timezone-aware, make now timezone-aware too
                        from datetime import timezone
                        now = datetime.now(timezone.utc)
                        if expiry.tzinfo != timezone.utc:
                            # Convert expiry to UTC if it's in a different timezone
                            expiry = expiry.astimezone(timezone.utc)
                    else:
                        # expiry is timezone-naive, use naive now
                        now = datetime.now()
                    
                    days_to_expiry = (expiry - now).days
                    if days_to_expiry < 0:
                        expiry_display = f"[red]Expired[/red]"
                    elif days_to_expiry < 30:
                        expiry_display = f"[red]{days_to_expiry}d[/red]"
                    elif days_to_expiry < 90:
                        expiry_display = f"[yellow]{days_to_expiry}d[/yellow]"
                    else:
                        expiry_display = f"{days_to_expiry}d"
                except Exception as e:
                    # Fallback in case of any datetime issues
                    expiry_display = "Error"
            else:
                expiry_display = "Unknown"
            
            # Format utilization
            util_percent = utilization['utilization_percent']
            if util_percent >= 90:
                util_display = f"[green]{util_percent:.1f}%[/green]"
            elif util_percent >= 70:
                util_display = f"[yellow]{util_percent:.1f}%[/yellow]"
            else:
                util_display = f"[red]{util_percent:.1f}%[/red]"
            
            # Accumulate totals
            total_capacity += utilization['total_capacity']
            total_used += utilization['used_capacity']
            total_available += utilization['remaining_capacity']
            
            table.add_row(
                ri_id[-20:] + "..." if len(ri_id) > 23 else ri_id,  # Truncate long IDs
                ri_details['DBInstanceClass'],
                ri_details['Engine'],
                "✓" if ri_details['MultiAZ'] else "✗",
                str(utilization['total_capacity']),
                str(utilization['used_capacity']),
                str(utilization['remaining_capacity']),
                util_display,
                ri_details['OfferingType'],
                f"${total_hourly_rate:.4f}",
                expiry_display
            )
        
        # Add summary row
        if total_capacity > 0:
            overall_utilization = (total_used / total_capacity) * 100
            if overall_utilization >= 90:
                overall_util_display = f"[green]{overall_utilization:.1f}%[/green]"
            elif overall_utilization >= 70:
                overall_util_display = f"[yellow]{overall_utilization:.1f}%[/yellow]"
            else:
                overall_util_display = f"[red]{overall_utilization:.1f}%[/red]"
            
            # Add divider
            divider_row = ["─" * 25, "─" * 15, "─" * 10, "─" * 8, "─" * 5, "─" * 4, "─" * 9, "─" * 10, "─" * 15, "─" * 10, "─" * 10]
            table.add_row(*divider_row, style="dim")
            
            # Add summary
            table.add_row(
                "[bold]TOTAL SUMMARY[/bold]",
                "",
                "",
                "",
                f"[bold]{total_capacity}[/bold]",
                f"[bold]{total_used}[/bold]",
                f"[bold]{total_available}[/bold]",
                f"[bold]{overall_util_display}[/bold]",
                "",
                "",
                "",
                style="bold cyan"
            )
        
        # Apply blur effect when help is shown
        if blur:
            # Create strong blur effect with multiple layers
            blurred_table = Panel(
                table, 
                style="dim bold",
                border_style="dim",
                padding=(0, 0)
            )
            return Panel(
                blurred_table,
                style="on grey11 dim",
                border_style="bright_black", 
                padding=(0, 0)
            )
        
        return table

    def render_layout():
        layout = Layout()
        has_multi_az = has_multi_az_instances()
        
        if show_help:
            # Show help as a bottom popup panel
            layout.split_column(
                Layout(name="main", ratio=3),
                Layout(name="help", ratio=2)
            )
            
            # Main content (table) with blur effect
            table = render_table(has_multi_az, blur=True)
            layout["main"].update(table)
            
            # Help popup at bottom
            help_panel = create_help_panel(has_multi_az)
            layout["help"].update(help_panel)
            
        else:
            # Normal mode - just the table, full screen
            layout.add_split(Layout(name="main"))
            
            # Show the appropriate table based on current view
            if current_view == 'ri_utilization' and ri_matches:
                table = create_ri_utilization_table()
            elif current_view == 'backup_maintenance':
                table = create_backup_maintenance_table()
            else:
                table = render_table(has_multi_az)
            layout["main"].update(table)
        
        return layout

    # Clear terminal and show loading
    clear_terminal()
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="Fetching and processing RDS data...", total=None)
        time.sleep(0.5)  # Simulate loading

    # Set up terminal for better Esc key handling
    setup_terminal_for_esc()
    
    # Interactive table with full screen - maximum responsiveness
    def cycle_view(direction=1):
        """Cycle through the three views: instances -> ri_utilization -> backup_maintenance -> instances"""
        nonlocal current_view
        views = ['instances']
        if ri_matches:
            views.append('ri_utilization')
        views.append('backup_maintenance')
        
        current_index = views.index(current_view)
        next_index = (current_index + direction) % len(views)
        current_view = views[next_index]

    with Live(render_layout(), refresh_per_second=4, console=console, screen=True) as live:
        controls_msg = "\nPress [bold]?[/bold] for help, [bold]m[/bold] to toggle monthly/hourly, [bold]b[/bold] for backup view"
        if ri_matches:
            controls_msg += ", [bold]v[/bold] for RI utilization"
        controls_msg += ", [bold]←/→[/bold] or [bold]Tab[/bold] to cycle views, [bold]q[/bold] to quit."
        console.print(controls_msg)
        while True:
            try:
                key = get_key_simple()
                if key is None:
                    continue
                
                # Handle exit keys - only q and Q for now (Esc disabled temporarily)
                if key in ['q', 'Q']:
                    clear_terminal()
                    return
                # Handle special keys - check for readchar constants and raw sequences
                elif (hasattr(readchar.key, 'RIGHT') and key == readchar.key.RIGHT) or key == '\x1b[C':
                    cycle_view(1)  # Cycle forward
                    live.update(render_layout())
                elif (hasattr(readchar.key, 'LEFT') and key == readchar.key.LEFT) or key == '\x1b[D':
                    cycle_view(-1)  # Cycle backward
                    live.update(render_layout())
                elif key == '\t':  # Regular Tab
                    cycle_view(1)  # Cycle forward
                    live.update(render_layout())
                elif key == '\x1b[Z':  # Shift+Tab (raw sequence)
                    cycle_view(-1)  # Cycle backward
                    live.update(render_layout())
                elif key == '?':
                    show_help = not show_help  # Toggle help
                    live.update(render_layout())
                elif key == 'm':  # Lowercase m for monthly toggle
                    show_monthly = not show_monthly  # Toggle monthly/hourly view
                    live.update(render_layout())
                elif key == 'V':  # Capital V for pricing view
                    current_view = 'instances'  # Direct to pricing view
                    live.update(render_layout())
                elif key == 'R' and ri_matches:  # Capital R for RI view
                    current_view = 'ri_utilization'  # Direct to RI utilization
                    live.update(render_layout())
                elif key == 'B':  # Capital B for backup view
                    current_view = 'backup_maintenance'  # Direct to backup maintenance
                    live.update(render_layout())
                else:
                    shortcuts = get_shortcuts()
                    key_lower = key.lower()
                    if key_lower in shortcuts:
                        if sort_state['key'] == shortcuts[key_lower]:
                            sort_state['ascending'] = not sort_state['ascending']
                        else:
                            sort_state['key'] = shortcuts[key_lower]
                            sort_state['ascending'] = True
                        live.update(render_layout())
            except KeyboardInterrupt:
                clear_terminal()
                return