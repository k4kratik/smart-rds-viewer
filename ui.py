from rich.console import Console, Group
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich import box
from rich.panel import Panel
import time
import readchar
from readchar import key as rkey
import os
import math

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
        {'name': 'EBS Throughput', 'key': 'storage_throughput', 'justify': 'right'},
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
    # Pagination state
    page_size = 10
    page_index = 0

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
        help_text += "  [bold]←[/bold] or [bold]Left Arrow[/bold]  = Previous page\n"
        help_text += "  [bold]→[/bold] or [bold]Right Arrow[/bold] = Next page\n"
        return Panel(help_text, title="Help", border_style="cyan")

    def render_table():
        # Prepare sorted rows and pagination
        rows = sort_rows(get_rows())
        total_pages = math.ceil(len(rows) / page_size) if rows else 1
        # Slice rows for current page
        start = page_index * page_size
        end = start + page_size
        display_rows = rows[start:end]
        # Create table with serial number column
        title = f"Amazon RDS Instances (Page {page_index+1}/{total_pages})"
        table = Table(title=title, box=box.SIMPLE_HEAVY)
        table.add_column("S.No.", justify="right")
        
        # Add columns dynamically
        for col in columns:
            table.add_column(col['name'], justify=col['justify'], style="bold" if col['key'] == 'name' else "")
        
        # Add data rows with serial numbers
        for idx, row in enumerate(display_rows):
            style = "red" if row['used_pct'] is not None and row['used_pct'] >= 80 else ""
            sno = start + idx + 1
            table.add_row(
                f"{sno}.",
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
        # Render the table followed by the help panel
        table = render_table()
        help_panel = create_help_panel()
        return Group(table, help_panel)

    # Clear terminal and show loading
    clear_terminal()
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="Fetching and processing RDS data...", total=None)
        time.sleep(0.5)  # Simulate loading

    # Interactive table with pagination and full screen
    with Live(render_layout(), refresh_per_second=4, console=console, screen=True) as live:
        console.print("\nPress [bold]q[/bold] to quit. Use [bold]←[/bold] / [bold]→[/bold] to change pages, or press the column key to sort.")
        while True:
            try:
                key = readchar.readkey()
                # Quit
                if key == '\x03' or key.lower() == 'q':
                    clear_terminal()
                    return
                # Next page
                if key == rkey.RIGHT:
                    total = math.ceil(len(sort_rows(get_rows())) / page_size)
                    if page_index < total - 1:
                        page_index += 1
                        live.update(render_layout())
                    continue
                # Previous page
                if key == rkey.LEFT:
                    if page_index > 0:
                        page_index -= 1
                        live.update(render_layout())
                    continue
                # Sorting shortcuts
                sk = key.lower()
                if sk in shortcuts:
                    if sort_state['key'] == shortcuts[sk]:
                        sort_state['ascending'] = not sort_state['ascending']
                    else:
                        sort_state['key'] = shortcuts[sk]
                        sort_state['ascending'] = True
                    live.update(render_layout())
            except KeyboardInterrupt:
                clear_terminal()
                return
