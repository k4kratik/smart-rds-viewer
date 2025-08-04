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
from fetch import is_aurora_instance

console = Console()

def clear_terminal():
    """Clear the terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')

def display_rds_table(rds_instances, metrics, pricing):
    # Define columns with their display names and sort keys
    columns = [
        {'name': 'Name', 'key': 'name', 'justify': 'left'},
        {'name': 'Class', 'key': 'class', 'justify': 'left'},
        {'name': 'Storage (GB)', 'key': 'storage', 'justify': 'right'},
        {'name': '% Used', 'key': 'used_pct', 'justify': 'right'},
        {'name': 'Free (GiB)', 'key': 'free_gb', 'justify': 'right'},
        {'name': 'IOPS', 'key': 'iops', 'justify': 'right'},
        {'name': 'EBS\nThroughput', 'key': 'storage_throughput', 'justify': 'right'},
        {'name': 'Instance\n($/hr)', 'key': 'instance_price', 'justify': 'right'},
        {'name': 'Storage\n($/hr)', 'key': 'storage_price', 'justify': 'right'},
        {'name': 'IOPS\n($/hr)', 'key': 'iops_price', 'justify': 'right'},
        {'name': 'EBS\nThroughput\n($/hr)', 'key': 'throughput_price', 'justify': 'right'},
        {'name': 'Total\n($/hr)', 'key': 'total_price', 'justify': 'right'},
    ]
    
    # Dynamic shortcut assignment - only lowercase letters
    def assign_shortcuts():
        shortcuts = {}
        available_letters = set('abcdefghijklmnopqrstuvwxyz')
        
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
    
    shortcuts = assign_shortcuts()
    
    sort_state = {'key': 'name', 'ascending': True}
    show_help = False

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
            display_name = f"{name} 👥" if is_multi_az else name
            
            price_info = pricing.get((klass, inst['Region'], inst['Engine']))
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
            
            if price_info is not None:
                if isinstance(price_info, dict):
                    instance_price = price_info.get('instance')
                    storage_price = price_info.get('storage')
                    iops_price = price_info.get('iops')
                    throughput_price = price_info.get('throughput')
                    total_price = price_info.get('total')
                else:
                    # Handle legacy format where price_info was just the instance price
                    instance_price = price_info
                    total_price = price_info
            
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
        }
        
        keyfunc = sort_funcs.get(k, lambda r: r['name'] or '')
        return sorted(rows, key=keyfunc, reverse=not ascending)

    def create_help_panel(has_multi_az=False):
        # Create compact horizontal layout - maintain column order
        help_items = []
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
        
        help_text += "\n[bold yellow]⌨️  Controls:[/bold yellow] [cyan]q[/cyan]=Quit  [cyan]?[/cyan]=Close Help  [cyan]ctrl+c[/cyan]=Exit"
        # Only show Multi-AZ explanation if there are Multi-AZ instances
        if has_multi_az:
            help_text += " [yellow]| 👥=Multi-AZ (2x pricing) | Press letter to sort, ? to close[/yellow]"
        else:
            help_text += " [yellow]| Press letter to sort, ? to close[/yellow]"
        
        return Panel(help_text, title="💡 Help & Shortcuts - Press ? to close", 
                    border_style="bright_blue", expand=True, padding=(0, 1))

    def render_table(has_multi_az=False):
        table = Table(title="Amazon RDS Instances", box=box.SIMPLE_HEAVY)
        
        # Add columns dynamically
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
            
            # Handle pricing columns
            storage_price_display = row['storage_price'] if row['storage_price'] == "N/A" else (f"${row['storage_price']:.4f}" if row['storage_price'] is not None else "?")
            iops_price_display = row['iops_price'] if row['iops_price'] == "N/A" else (f"${row['iops_price']:.4f}" if row['iops_price'] is not None else "?")
            throughput_price_display = row['throughput_price'] if row['throughput_price'] == "N/A" else (f"${row['throughput_price']:.4f}" if row['throughput_price'] is not None else "?")
            
            table.add_row(
                str(row['name']),
                str(row['class']),
                str(row['storage']),
                used_pct_display,
                free_gb_display,
                iops_display,
                throughput_display,
                f"${row['instance_price']:.4f}" if row['instance_price'] is not None else "?",
                storage_price_display,
                iops_price_display,
                throughput_price_display,
                f"${row['total_price']:.4f}" if row['total_price'] is not None else "?"
            )
        
        # Calculate totals for pricing columns
        total_instance_price = 0
        total_storage_price = 0
        total_iops_price = 0
        total_throughput_price = 0
        total_overall_price = 0
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
        
        # Add divider row
        divider_row = ["─" * 20] + ["─" * 15] * (len(columns) - 1)
        table.add_row(*divider_row, style="dim")
        
        # Add totals row
        total_row = [
            f"[bold]TOTAL ({instance_count} instances)[/bold]",  # Name column
            "",  # Class column
            "",  # Storage column  
            "",  # % Used column
            "",  # Free column
            "",  # IOPS column
            "",  # Throughput column
            f"[bold]${total_instance_price:.4f}[/bold]",  # Instance pricing
            f"[bold]${total_storage_price:.4f}[/bold]",   # Storage pricing
            f"[bold]${total_iops_price:.4f}[/bold]",      # IOPS pricing
            f"[bold]${total_throughput_price:.4f}[/bold]", # Throughput pricing
            f"[bold]${total_overall_price:.4f}[/bold]"     # Total pricing
        ]
        table.add_row(*total_row, style="bold cyan")
        
        # Add monthly estimate row with enhanced visibility
        monthly_total = total_overall_price * 24 * 30.42  # Average month
        monthly_row = [
            f"[bold magenta]📅 Monthly Estimate[/bold magenta]",  # Name column with emoji
            "",  # Class column
            "",  # Storage column  
            "",  # % Used column
            "",  # Free column
            "",  # IOPS column
            "",  # Throughput column
            f"[bold magenta]${total_instance_price * 24 * 30.42:.2f}[/bold magenta]",  # Instance pricing
            f"[bold magenta]${total_storage_price * 24 * 30.42:.2f}[/bold magenta]",   # Storage pricing
            f"[bold magenta]${total_iops_price * 24 * 30.42:.2f}[/bold magenta]",      # IOPS pricing
            f"[bold magenta]${total_throughput_price * 24 * 30.42:.2f}[/bold magenta]", # Throughput pricing
            f"[bold bright_magenta]${monthly_total:.2f}[/bold bright_magenta]"          # Total pricing - extra bright
        ]
        table.add_row(*monthly_row, style="bold magenta")
        
        # Add multi-AZ explanation note only if there are Multi-AZ instances
        if has_multi_az:
            note_row = [
                f"[dim]👥 = Multi-AZ (2x pricing)[/dim]",  # Name column with note
                "",  # Class column
                "",  # Storage column  
                "",  # % Used column
                "",  # Free column
                "",  # IOPS column
                "",  # Throughput column
                "",  # Instance pricing
                "",  # Storage pricing
                "",  # IOPS pricing
                "",  # Throughput pricing
                ""   # Total pricing
            ]
            table.add_row(*note_row, style="dim")
        
        # Update table title to include monthly total for visibility
        table.title = f"Amazon RDS Instances - Monthly Est: ${monthly_total:.2f} ({instance_count} instances)"
        
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
            table = render_table(has_multi_az)
            layout["main"].update(table)
        
        return layout

    # Clear terminal and show loading
    clear_terminal()
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="Fetching and processing RDS data...", total=None)
        time.sleep(0.5)  # Simulate loading

    # Interactive table with full screen
    with Live(render_layout(), refresh_per_second=4, console=console, screen=True) as live:
        console.print("\nPress [bold]?[/bold] for help, [bold]q[/bold] to quit.")
        while True:
            try:
                key = readchar.readkey().lower()
                if key in ['q', '\x03']:  # q or Ctrl+C
                    clear_terminal()
                    return
                elif key == '?':
                    show_help = not show_help  # Toggle help
                    live.update(render_layout())
                elif key in shortcuts:
                    if sort_state['key'] == shortcuts[key]:
                        sort_state['ascending'] = not sort_state['ascending']
                    else:
                        sort_state['key'] = shortcuts[key]
                        sort_state['ascending'] = True
                    live.update(render_layout())
            except KeyboardInterrupt:
                clear_terminal()
                return