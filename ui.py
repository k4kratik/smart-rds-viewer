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
from datetime import datetime
from fetch import is_aurora_instance

console = Console()

def clear_terminal():
    """Clear the terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')

def display_rds_table(rds_instances, metrics, pricing, ri_matches=None):
    
    sort_state = {'key': 'name', 'ascending': True}
    show_help = False
    show_monthly = False  # Toggle between hourly and monthly view
    show_ri_table = False  # Toggle between instance table and RI utilization table
    
    def get_columns():
        """Get column definitions based on current view mode."""
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
    
    # Dynamic shortcut assignment - only lowercase letters
    def assign_shortcuts():
        shortcuts = {}
        available_letters = set('abcdefghijklmnopqrstuvwxyz')
        columns = get_columns()
        
        for col in columns:
            # Try first letter of column name
            col_name_clean = ''.join(c.lower() for c in col['name'] if c.isalpha())
            preferred_letter = col_name_clean[0] if col_name_clean else None
            
            if preferred_letter and preferred_letter in available_letters:
                shortcuts[preferred_letter] = col['key']
                available_letters.remove(preferred_letter)
            else:
                # Try other letters from the column name
                assigned = False
                for letter in col_name_clean:
                    if letter in available_letters:
                        shortcuts[letter] = col['key']
                        available_letters.remove(letter)
                        assigned = True
                        break
                
                # If still not assigned, use any available letter
                if not assigned and available_letters:
                    letter = available_letters.pop()
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
            'storage': lambda r: 0 if r['storage'] == "Aurora" else (r['storage'] or 0),
            'used_pct': lambda r: -1 if r['used_pct'] == "N/A" else (r['used_pct'] if r['used_pct'] is not None else 0),
            'free_gb': lambda r: -1 if r['free_gb'] == "N/A" else (r['free_gb'] if r['free_gb'] is not None else 0),
            'iops': lambda r: -1 if r['iops'] in ["N/A", "gp2"] else (r['iops'] if r['iops'] is not None else 0),
            'storage_throughput': lambda r: -1 if r['storage_throughput'] in ["N/A", "gp2"] else (r['storage_throughput'] if r['storage_throughput'] is not None else 0),

            'instance_price': lambda r: (r['instance_price'] if r['instance_price'] is not None else float('inf')),
            'storage_price': lambda r: float('inf') if r['storage_price'] == "N/A" else (r['storage_price'] if r['storage_price'] is not None else float('inf')),
            'iops_price': lambda r: float('inf') if r['iops_price'] == "N/A" else (r['iops_price'] if r['iops_price'] is not None else float('inf')),
            'throughput_price': lambda r: float('inf') if r['throughput_price'] == "N/A" else (r['throughput_price'] if r['throughput_price'] is not None else float('inf')),
            'total_price': lambda r: (r['total_price'] if r['total_price'] is not None else float('inf')),
            'ri_savings': lambda r: (r['ri_savings'] if r.get('ri_savings') is not None else 0),
        }
        
        keyfunc = sort_funcs.get(k, lambda r: r['name'] or '')
        return sorted(rows, key=keyfunc, reverse=not ascending)

    def create_help_panel(has_multi_az=False):
        # Create compact horizontal layout - maintain column order
        help_items = []
        columns = get_columns()
        shortcuts = assign_shortcuts()
        # Iterate through columns in their original order to maintain table sequence
        for col in columns:
            # Find the shortcut key for this column
            key = next((k for k, v in shortcuts.items() if v == col['key']), None)
            if key:
                # Clean up column name for display
                col_name_clean = col['name'].replace('\n', ' ').strip()  # Remove newlines and extra spaces
                # Shorten common terms for more compact display
                col_name_clean = col_name_clean.replace('($/hr)', 'pricing').replace('EBS Throughput', 'Throughput')
                help_items.append(f"[cyan]{key}[/cyan]={col_name_clean}")
        
        # Arrange shortcuts in horizontal rows (4 items per row) with proper spacing
        items_per_row = 4
        help_text = "[bold yellow]📋 Sorting Shortcuts:[/bold yellow]\n"
        
        for i in range(0, len(help_items), items_per_row):
            row_items = help_items[i:i + items_per_row]
            # Format each item with better spacing - wider for 'pricing' text
            formatted_items = [f"{item:<22}" for item in row_items]
            help_text += "  " + "  ".join(formatted_items) + "\n"
        
        help_text += "\n[bold yellow]⌨️  Controls:[/bold yellow] [cyan]q[/cyan]=Quit  [cyan]?[/cyan]=Close Help  [cyan]ctrl+c[/cyan]=Exit\n"
        
        # Pricing view controls
        pricing_controls = "[bold yellow]💰 Pricing View:[/bold yellow] [cyan]m[/cyan]=Toggle Monthly/Hourly pricing display"
        if ri_matches:
            pricing_controls += "  [cyan]u[/cyan]=Toggle RI Utilization Table"
        help_text += pricing_controls + "\n"
        
        # Visual indicators
        if ri_matches or has_multi_az:
            help_text += "[bold yellow]🎨 Visual Indicators:[/bold yellow] "
            indicators = []
            if ri_matches:
                indicators.append("Instance names: [green]Green=100% RI[/green] [yellow]Yellow=Partial RI[/yellow]")
            if has_multi_az:
                indicators.append("👥=Multi-AZ (2x pricing)")
            help_text += "  ".join(indicators) + "\n"
        
        # General instructions
        help_text += "[bold yellow]📋 Instructions:[/bold yellow] Press any letter to sort by that column, ? to close this help menu."
        
        return Panel(help_text, title="💡 Help & Shortcuts - Press ? to close this help menu.", 
                    border_style="bright_blue", expand=True, padding=(0, 1))

    def render_table(has_multi_az=False):
        table = Table(title="Amazon RDS Instances", box=box.SIMPLE_HEAVY)
        
        # Add columns dynamically
        columns = get_columns()
        for col in columns:
            if col['key'] == 'name':
                # Name column with reduced width - more compact but readable
                table.add_column(col['name'], justify=col['justify'], style="bold", min_width=18, no_wrap=True)
            else:
                table.add_column(col['name'], justify=col['justify'], style="bold" if col['key'] == 'name' else "")
        
        rows = sort_rows(get_rows())
        for row in rows:
            is_aurora = row.get('is_aurora', False)
            
            # Handle % Used column - Color only if >= 80% and not Aurora
            if row['used_pct'] == "N/A":
                used_pct_display = "N/A"
            elif row['used_pct'] is not None and row['used_pct'] >= 80:
                used_pct_display = f"[red]{row['used_pct']:.1f}%[/red]"
            else:
                used_pct_display = f"{row['used_pct']:.1f}%" if row['used_pct'] is not None else "?"
            
            # Handle Free (GiB) column
            if row['free_gb'] == "N/A":
                free_gb_display = "N/A"
            else:
                free_gb_display = f"{row['free_gb']:.1f}" if row['free_gb'] is not None else "?"
            
            # Handle IOPS and Storage Throughput
            if row['iops'] == "N/A":
                iops_display = "N/A"
            elif row['iops'] == "gp2":
                iops_display = "gp2"
            elif row['iops'] is not None:
                iops_display = str(row['iops'])
            else:
                iops_display = "-"
                
            if row['storage_throughput'] == "N/A":
                throughput_display = "N/A"
            elif row['storage_throughput'] == "gp2":
                throughput_display = "gp2"
            elif row['storage_throughput'] is not None:
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
                    return f"${adjusted_price:.{price_precision}f}"
                else:
                    return "?"
            
            storage_price_display = format_price(row['storage_price'], row['storage_price'])
            iops_price_display = format_price(row['iops_price'], row['iops_price'])
            throughput_price_display = format_price(row['throughput_price'], row['throughput_price'])
            instance_price_display = format_price(row['instance_price'], row['instance_price'])
            total_price_display = format_price(row['total_price'], row['total_price'])
            ri_savings_display = format_price(row['ri_savings'], row['ri_savings']) if row.get('ri_savings') is not None else None
            
            # Build row data dynamically based on columns
            row_data = []
            for col in columns:
                if col['key'] == 'name':
                    row_data.append(str(row['name']))
                elif col['key'] == 'class':
                    row_data.append(str(row['class']))
                elif col['key'] == 'storage':
                    row_data.append(str(row['storage']))
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
        
        # Calculate totals for pricing columns
        total_instance_price = 0
        total_storage_price = 0
        total_iops_price = 0
        total_throughput_price = 0
        total_overall_price = 0
        total_ri_savings = 0
        instance_count = 0
        
        for row in rows:
            # Count instances (skip if pricing data is missing)
            if row['instance_price'] is not None:
                instance_count += 1
                
            # Sum instance pricing (skip "N/A" values)
            if row['instance_price'] is not None and isinstance(row['instance_price'], (int, float)):
                total_instance_price += row['instance_price']
                
            # Sum storage pricing (skip "N/A" values)
            if (row['storage_price'] != "N/A" and row['storage_price'] is not None and 
                isinstance(row['storage_price'], (int, float))):
                total_storage_price += row['storage_price']
                
            # Sum IOPS pricing (skip "N/A" values)
            if (row['iops_price'] != "N/A" and row['iops_price'] is not None and 
                isinstance(row['iops_price'], (int, float))):
                total_iops_price += row['iops_price']
                
            # Sum throughput pricing (skip "N/A" values)
            if (row['throughput_price'] != "N/A" and row['throughput_price'] is not None and 
                isinstance(row['throughput_price'], (int, float))):
                total_throughput_price += row['throughput_price']
                
            # Sum total pricing (skip "N/A" values)
            if row['total_price'] is not None and isinstance(row['total_price'], (int, float)):
                total_overall_price += row['total_price']
                
            # Sum RI savings
            if row.get('ri_savings') is not None and isinstance(row['ri_savings'], (int, float)):
                total_ri_savings += row['ri_savings']
        
        # Add divider row
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
        
        table.add_row(*total_row, style="bold cyan")
        
        # Add monthly estimate row only when in hourly view
        if not show_monthly:
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
                    monthly_row.append(f"[bold bright_green]${monthly_ri_savings:.2f}[/bold bright_green]")
            
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
        
        # Update table title based on current view mode with RI information
        view_mode = "Monthly" if show_monthly else "Hourly"
        
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
            table.title = f"Amazon RDS Instances ({view_mode}) - Total: ${total_display:.2f}/mo | Daily: ${daily_total:.2f}/day ({instance_count} instances){ri_info}"
        else:
            daily_total = total_overall_price * 24
            monthly_total = total_overall_price * 24 * 30.42
            table.title = f"Amazon RDS Instances ({view_mode}) - Total: ${total_overall_price:.4f}/hr | Daily: ${daily_total:.2f}/day | Monthly: ${monthly_total:.2f}/mo ({instance_count} instances){ri_info}"
        
        return table

    def create_ri_utilization_table():
        """Create a table showing Reserved Instance utilization."""
        if not ri_matches or not ri_matches.get('ri_utilization'):
            # Create empty table with message
            table = Table(title="Reserved Instance Utilization - No RIs found", box=box.SIMPLE_HEAVY)
            table.add_column("Message", justify="center", style="dim")
            table.add_row("No Reserved Instances found in this region.")
            return table
        
        table = Table(title="Reserved Instance Utilization", box=box.SIMPLE_HEAVY)
        
        # Add columns
        table.add_column("RI ID", justify="left", style="bold", min_width=25)
        table.add_column("Instance Class", justify="left")
        table.add_column("Engine", justify="left")
        table.add_column("Multi-AZ", justify="center")
        table.add_column("Total", justify="center")
        table.add_column("Used", justify="center")
        table.add_column("Available", justify="center")
        table.add_column("Utilization", justify="center")
        table.add_column("Offering Type", justify="left")
        table.add_column("Hourly Rate", justify="right")
        table.add_column("Expires", justify="left")
        
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
            
            # Main content (table)
            table = render_table(has_multi_az)
            layout["main"].update(table)
            
            # Help popup at bottom
            help_panel = create_help_panel(has_multi_az)
            layout["help"].update(help_panel)
            
        else:
            # Normal mode - just the table, full screen
            layout.add_split(Layout(name="main"))
            
            # Show either instance table or RI utilization table
            if show_ri_table and ri_matches:
                table = create_ri_utilization_table()
            else:
                table = render_table(has_multi_az)
            layout["main"].update(table)
        
        return layout

    # Clear terminal and show loading
    clear_terminal()
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="Fetching and processing RDS data...", total=None)
        time.sleep(0.5)  # Simulate loading

    # Interactive table with full screen - maximum responsiveness
    with Live(render_layout(), refresh_per_second=4, console=console, screen=True) as live:
        controls_msg = "\nPress [bold]?[/bold] for help, [bold]m[/bold] to toggle monthly/hourly"
        if ri_matches:
            controls_msg += ", [bold]u[/bold] for RI utilization"
        controls_msg += ", [bold]q[/bold] to quit."
        console.print(controls_msg)
        while True:
            try:
                key = readchar.readkey().lower()
                if key in ['q', '\x03']:  # q or Ctrl+C
                    clear_terminal()
                    return
                elif key == '?':
                    show_help = not show_help  # Toggle help
                    live.update(render_layout())
                elif key == 'm':
                    show_monthly = not show_monthly  # Toggle monthly/hourly view
                    live.update(render_layout())
                elif key == 'u' and ri_matches:
                    show_ri_table = not show_ri_table  # Toggle RI utilization table
                    live.update(render_layout())
                elif key in assign_shortcuts():
                    shortcuts = assign_shortcuts()
                    if sort_state['key'] == shortcuts[key]:
                        sort_state['ascending'] = not sort_state['ascending']
                    else:
                        sort_state['key'] = shortcuts[key]
                        sort_state['ascending'] = True
                    live.update(render_layout())
            except KeyboardInterrupt:
                clear_terminal()
                return