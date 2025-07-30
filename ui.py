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
        {'name': 'EBS Tput', 'key': 'storage_throughput', 'justify': 'right'},
        {'name': 'Price ($/hr)', 'key': 'price', 'justify': 'right'},
    ]
    
    # Auto-assign shortcuts: first letter of each column name
    shortcuts = {}
    for i, col in enumerate(columns):
        # Use first letter, or second letter if first is taken
        first_letter = col['name'].split()[0][0].lower()
        if first_letter not in shortcuts:
            shortcuts[first_letter] = col['key']
        else:
            # Try second word or second letter
            words = col['name'].split()
            if len(words) > 1:
                second_letter = words[1][0].lower()
                if second_letter not in shortcuts:
                    shortcuts[second_letter] = col['key']
                else:
                    # Use a number as fallback
                    shortcuts[str(i)] = col['key']
            else:
                # Use second letter of first word
                if len(col['name']) > 1:
                    second_letter = col['name'][1].lower()
                    if second_letter not in shortcuts:
                        shortcuts[second_letter] = col['key']
                    else:
                        shortcuts[str(i)] = col['key']
                else:
                    shortcuts[str(i)] = col['key']
    
    sort_state = {'key': 'name', 'ascending': True}
    show_help = False

    def get_rows():
        rows = []
        for inst in rds_instances:
            name = inst['DBInstanceIdentifier']
            klass = inst['DBInstanceClass']
            storage = inst['AllocatedStorage']
            iops = inst.get('Iops')
            storage_throughput = inst.get('StorageThroughput')
            price = pricing.get((klass, inst['Region'], inst['Engine']))
            free = metrics.get(name)
            if free is not None and storage:
                used_pct = 100 - (free / (storage * 1024**3) * 100)
                free_gb = free / (1024**3)  # Convert bytes to GB
            else:
                used_pct = None
                free_gb = None
            rows.append({
                'name': name,
                'class': klass,
                'storage': storage,
                'used_pct': used_pct,
                'free_gb': free_gb,
                'iops': iops,
                'storage_throughput': storage_throughput,
                'price': price,
            })
        return rows

    def sort_rows(rows):
        k = sort_state['key']
        ascending = sort_state['ascending']
        
        # Define sort functions for each column type
        sort_funcs = {
            'name': lambda r: r['name'] or '',
            'class': lambda r: r['class'] or '',
            'storage': lambda r: r['storage'] or 0,
            'used_pct': lambda r: (r['used_pct'] if r['used_pct'] is not None else 0),
            'free_gb': lambda r: (r['free_gb'] if r['free_gb'] is not None else 0),
            'iops': lambda r: (r['iops'] if r['iops'] is not None else 0),
            'storage_throughput': lambda r: (r['storage_throughput'] if r['storage_throughput'] is not None else 0),
            'price': lambda r: (r['price'] if r['price'] is not None else float('inf')),
        }
        
        keyfunc = sort_funcs.get(k, lambda r: r['name'] or '')
        return sorted(rows, key=keyfunc, reverse=not ascending)

    def create_help_panel():
        help_text = "[bold cyan]Sorting Shortcuts:[/bold cyan]\n"
        for key, col_key in shortcuts.items():
            # Find the column name for this key
            col_name = next((col['name'] for col in columns if col['key'] == col_key), col_key)
            help_text += f"  [bold]{key}[/bold] = {col_name}\n"
        help_text += "\n[bold cyan]Other Commands:[/bold cyan]\n"
        help_text += "  [bold]q[/bold] = Quit\n"
        help_text += "  [bold]?[/bold] = Toggle this help\n"
        help_text += "  [bold]Ctrl+C[/bold] = Quit\n"
        return Panel(help_text, title="Help", border_style="cyan")

    def render_table():
        table = Table(title="Amazon RDS Instances", box=box.SIMPLE_HEAVY)
        
        # Add columns dynamically
        for col in columns:
            table.add_column(col['name'], justify=col['justify'], style="bold" if col['key'] == 'name' else "")
        
        rows = sort_rows(get_rows())
        for row in rows:
            style = "red" if row['used_pct'] is not None and row['used_pct'] >= 80 else ""
            table.add_row(
                str(row['name']),
                str(row['class']),
                str(row['storage']),
                f"{row['used_pct']:.1f}%" if row['used_pct'] is not None else "?",
                f"{row['free_gb']:.1f}" if row['free_gb'] is not None else "?",
                str(row['iops']) if row['iops'] is not None else "-",
                str(row['storage_throughput']) if row['storage_throughput'] is not None else "-",
                f"${row['price']:.4f}" if row['price'] is not None else "?",
                style=style
            )
        return table

    def render_layout():
        layout = Layout()
        layout.split_column(
            Layout(name="main", ratio=3),
            Layout(name="help", ratio=1)
        )
        
        # Main content (table)
        table = render_table()
        layout["main"].update(table)
        
        # Help panel (shown/hidden based on show_help)
        if show_help:
            help_panel = create_help_panel()
            layout["help"].update(help_panel)
        else:
            layout["help"].update("")
        
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