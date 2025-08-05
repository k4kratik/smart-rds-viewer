import boto3
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from botocore.config import Config

# Cache configuration
CACHE_FILE = "/tmp/rds_pricing_cache.json"
CACHE_DURATION_HOURS = 24  # Cache for 24 hours

# Optimized boto3 configuration
OPTIMIZED_CONFIG = Config(
    # Connection pooling - reuse connections
    max_pool_connections=50,
    # Retry configuration  
    retries={'max_attempts': 3, 'mode': 'adaptive'},
    # HTTP configuration
    connect_timeout=10,
    read_timeout=30
)

# Thread-local storage for boto3 sessions
_local = threading.local()

def get_optimized_pricing_client():
    """Get thread-local optimized pricing client with connection pooling."""
    if not hasattr(_local, 'pricing_client'):
        # Create a new session with optimized configuration
        session = boto3.Session()
        _local.pricing_client = session.client('pricing', 
                                             region_name='us-east-1',
                                             config=OPTIMIZED_CONFIG)
    return _local.pricing_client


def tuple_to_key(tuple_key):
    """Convert tuple key to string for JSON serialization."""
    return f"{tuple_key[0]}|{tuple_key[1]}|{tuple_key[2]}"


def key_to_tuple(string_key):
    """Convert string key back to tuple for internal use."""
    parts = string_key.split("|")
    return (parts[0], parts[1], parts[2])


def clear_pricing_cache():
    """Delete the pricing cache file if it exists."""
    try:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            print("[INFO] Pricing cache cleared.")
            return True
        else:
            print("[INFO] No pricing cache file found.")
            return False
    except Exception as e:
        print(f"[WARN] Error clearing cache: {e}")
        return False


def load_cached_pricing(nocache=False):
    """Load pricing data from cache if it exists and is valid."""
    if nocache:
        clear_pricing_cache()
        return None
        
    try:
        if not os.path.exists(CACHE_FILE):
            return None

        with open(CACHE_FILE, "r") as f:
            cache_data = json.load(f)

        # Check if cache is still valid
        cache_time = datetime.fromisoformat(cache_data["timestamp"])
        if datetime.now() - cache_time > timedelta(hours=CACHE_DURATION_HOURS):
            print("[INFO] Pricing cache expired, fetching fresh data...")
            return None

        # Convert string keys back to tuples
        prices = {}
        for string_key, price in cache_data["prices"].items():
            tuple_key = key_to_tuple(string_key)
            prices[tuple_key] = price

        print("[INFO] Using cached pricing data...")
        return prices
    except Exception as e:
        print(f"[WARN] Error loading cache: {e}")
        return None


def save_cached_pricing(prices):
    """Save pricing data to cache."""
    try:
        # Convert tuple keys to strings for JSON serialization
        serializable_prices = {}
        for tuple_key, price in prices.items():
            string_key = tuple_to_key(tuple_key)
            serializable_prices[string_key] = price

        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "prices": serializable_prices,
        }
        with open(CACHE_FILE, "w") as f:
            json.dump(cache_data, f, indent=2)
        print("[INFO] Pricing data cached successfully.")
    except Exception as e:
        print(f"[WARN] Error saving cache: {e}")


def get_rds_pricing_data_optimized(region: str, engine: str, instance_types: set, data_type: str) -> List[Dict]:
    """
    Optimized pricing data fetch with aggressive filtering and smaller result sets.
    """
    client = get_optimized_pricing_client()
    
    # Base filters for instance data
    base_filters = [
        {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
        {"Type": "TERM_MATCH", "Field": "databaseEngine", "Value": engine},
    ]
    
    pricing_data = []
    next_token = None
    max_results = 50  # Smaller result sets for faster processing
    
    while True:
        # Build request parameters
        params = {
            "ServiceCode": "AmazonRDS",
            "Filters": base_filters,
            "MaxResults": max_results
        }
        if next_token:
            params["NextToken"] = next_token

        # Make API call
        response = client.get_products(**params)
        
        # Process current page with early filtering
        for product_json in response["PriceList"]:
            product = json.loads(product_json)
            attributes = product.get("product", {}).get("attributes", {})
            
            # Early filtering by instance type to reduce processing
            instance_type = attributes.get("instanceType", "")
            if instance_type and instance_type not in instance_types:
                continue
            
            usage_type = attributes.get("usagetype", "").lower()
            
            # Get all pricing terms
            terms = product.get("terms", {}).get("OnDemand", {})
            for term_data in terms.values():
                for price_dim in term_data.get("priceDimensions", {}).values():
                    price_info = {
                        "Description": price_dim.get("description"),
                        "UsageType": usage_type,
                        "Price (USD)": price_dim["pricePerUnit"].get("USD", "N/A"),
                        "Unit": price_dim.get("unit", ""),
                        "StorageType": attributes.get("volumeType", ""),
                        "DeploymentOption": attributes.get("deploymentOption", ""),
                        "Engine": attributes.get("databaseEngine", ""),
                        "Region": attributes.get("regionCode", ""),
                        "InstanceType": instance_type,
                    }
                    pricing_data.append(price_info)
        
        # Check for more pages - but limit to reasonable amount
        next_token = response.get("NextToken")
        if not next_token or len(pricing_data) > 1000:  # Safety limit
            break

    return pricing_data


def get_rds_pricing_data(region: str = "ap-south-1", engine: str = "MySQL", filters: List[Dict] = None) -> List[Dict]:
    """
    Fetch RDS pricing information based on provided filters.
    Returns raw pricing data that includes all components (storage, IOPS, throughput, etc.)
    for different storage types (gp3, io1, io2, etc.) and deployment modes.
    
    Args:
        region: AWS region code (e.g., ap-south-1)
        engine: Database engine (e.g., MySQL, PostgreSQL)
        filters: Additional filters to apply to the pricing API query
    """
    # Use optimized client with connection pooling
    client = get_optimized_pricing_client()
    
    # Base filters
    base_filters = [
        {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
        {"Type": "TERM_MATCH", "Field": "databaseEngine", "Value": engine},
    ]
    
    # Combine with additional filters if provided
    if filters:
        base_filters.extend(filters)

    pricing_data = []
    next_token = None

    while True:
        # Build request parameters
        params = {
            "ServiceCode": "AmazonRDS",
            "Filters": base_filters,
            "MaxResults": 100
        }
        if next_token:
            params["NextToken"] = next_token

        # Make API call
        response = client.get_products(**params)
        
        # Process current page
        for product_json in response["PriceList"]:
            product = json.loads(product_json)
            attributes = product.get("product", {}).get("attributes", {})
            usage_type = attributes.get("usagetype", "").lower()
            
            # Get all pricing terms
            terms = product.get("terms", {}).get("OnDemand", {})
            for term_data in terms.values():
                for price_dim in term_data.get("priceDimensions", {}).values():
                    price_info = {
                        "Description": price_dim.get("description"),
                        "UsageType": usage_type,
                        "Price (USD)": price_dim["pricePerUnit"].get("USD", "N/A"),
                        "Unit": price_dim.get("unit", ""),
                        # Include additional attributes that might be useful
                        "StorageType": attributes.get("volumeType", ""),
                        "DeploymentOption": attributes.get("deploymentOption", ""),
                        "Engine": attributes.get("databaseEngine", ""),
                        "Region": attributes.get("regionCode", ""),
                        "InstanceType": attributes.get("instanceType", ""),
                    }
                    pricing_data.append(price_info)

        # Check for more pages
        next_token = response.get("NextToken")
        if not next_token:
            break

    return pricing_data


def parse_pricing_components(pricing_data, instance_class, storage_type, allocated_storage, iops):
    """Parse pricing data to extract instance, storage, and IOPS costs."""
    instance_price = 0
    storage_price_per_gb = 0
    iops_price_per_iop = 0
    storage_cost_monthly = 0
    iops_cost_monthly = 0
    
    print(f"[DEBUG] Parsing pricing for {instance_class}, storage: {storage_type}, allocated: {allocated_storage}GB, IOPS: {iops}")
    print(f"[DEBUG] Total pricing items to examine: {len(pricing_data)}")
    
    for i, item in enumerate(pricing_data):
        description = item.get("Description", "").lower()
        usage_type = item.get("UsageType", "").lower()
        price_str = item.get("Price (USD)", "0")
        unit = item.get("Unit", "").lower()
        item_instance_type = item.get("InstanceType", "")
        item_storage_type = item.get("StorageType", "")
        
        # Debug: Print first few items to understand the data structure
        if i < 5:
            print(f"[DEBUG] Item {i}: Description='{item.get('Description', '')}', "
                  f"UsageType='{item.get('UsageType', '')}', "
                  f"Price='{price_str}', Unit='{item.get('Unit', '')}', "
                  f"InstanceType='{item_instance_type}', "
                  f"StorageType='{item_storage_type}'")
        
        # Skip if price is not available
        if price_str == "N/A" or not price_str:
            continue
            
        try:
            price = float(price_str)
        except ValueError:
            continue
        
        if price <= 0:
            continue
        
        # Instance pricing (hourly) - be more flexible with matching
        if (item_instance_type == instance_class and 
            ("hour" in unit or "hrs" in unit)):
            instance_price = price
            print(f"[DEBUG] Found instance price: ${price}/hr for {instance_class}")
        
        # Storage pricing (monthly per GB) - be more flexible
        elif (("storage" in description or storage_type.lower() in description) and
              "gb" in unit and "month" in unit and
              (not item_storage_type or item_storage_type.lower() == storage_type.lower())):
            storage_price_per_gb = price
            storage_cost_monthly = storage_price_per_gb * allocated_storage
            print(f"[DEBUG] Found storage price: ${price}/GB-month for {storage_type}")
        
        # IOPS pricing (monthly per IOPS) - be more flexible
        elif (("iops" in description or "piops" in usage_type or "provisioned" in description) and
              ("iops" in unit or "provisioned" in unit) and "month" in unit):
            iops_price_per_iop = price
            if iops and iops > 0:
                # For gp3 volumes, the first 3,000 IOPS are included for free
                if storage_type.lower() == "gp3" and iops > 3000:
                    billable_iops = iops - 3000  # Only charge for IOPS above the free baseline
                    iops_cost_monthly = iops_price_per_iop * billable_iops
                elif storage_type.lower() == "gp3" and iops <= 3000:
                    iops_cost_monthly = 0  # All IOPS are within the free baseline
                else:
                    # For io1, io2, and other storage types, charge for all IOPS
                    iops_cost_monthly = iops_price_per_iop * iops
            print(f"[DEBUG] Found IOPS price: ${price}/IOPS-month")
    
    print(f"[DEBUG] Final prices - Instance: ${instance_price}, Storage: ${storage_cost_monthly/730:.4f}/hr, IOPS: ${iops_cost_monthly/730:.4f}/hr")
    
    return {
        "instance": instance_price,  # Already hourly
        "storage": storage_cost_monthly / 730 if storage_cost_monthly > 0 else 0,  # Convert monthly to hourly
        "iops": iops_cost_monthly / 730 if iops_cost_monthly > 0 else 0,  # Convert monthly to hourly
        "total": instance_price + (storage_cost_monthly / 730) + (iops_cost_monthly / 730)
    }


def parse_pricing_components_v2(instance_data, storage_data, iops_data, throughput_data, instance_class, storage_type, allocated_storage, iops, storage_throughput):
    """Parse pricing data from separate datasets for instance, storage, IOPS, and throughput costs."""
    instance_price = 0
    storage_cost_monthly = 0
    iops_cost_monthly = 0
    throughput_cost_monthly = 0
    
    # Parse instance pricing
    for item in instance_data:
        item_instance_type = item.get("InstanceType", "")
        price_str = item.get("Price (USD)", "0")
        unit = item.get("Unit", "").lower()
        
        if (item_instance_type == instance_class and 
            ("hour" in unit or "hrs" in unit) and
            price_str != "N/A" and price_str):
            try:
                price = float(price_str)
                if price > 0:
                    instance_price = price
                    break
            except ValueError:
                continue
    
    # Parse storage pricing
    # Map our storage types to AWS storage type names
    storage_type_map = {
        "gp3": "General Purpose-GP3",
        "gp2": "General Purpose",
        "io1": "Provisioned IOPS",
        "io2": "Provisioned IOPS-IO2",
        "magnetic": "Magnetic"
    }
    
    target_storage_type = storage_type_map.get(storage_type.lower(), storage_type)
    
    for item in storage_data:
        description = item.get("Description", "").lower()
        price_str = item.get("Price (USD)", "0")
        unit = item.get("Unit", "")
        item_storage_type = item.get("StorageType", "")
        usage_type = item.get("UsageType", "").lower()
        
        # Look for Single-AZ storage (avoid Multi-AZ unless specified)
        is_single_az = "multi-az" not in usage_type and "multi-azcluster" not in usage_type
        
        # Match by StorageType field first (more reliable)
        if (item_storage_type == target_storage_type and
            unit == "GB-Mo" and is_single_az and
            price_str != "N/A" and price_str):
            try:
                price = float(price_str)
                if price > 0:
                    storage_cost_monthly = price * allocated_storage
                    break
            except ValueError:
                continue
        
        # Fallback: match by description for storage type in description
        elif (storage_type.lower() in description and
              unit == "GB-Mo" and is_single_az and
              price_str != "N/A" and price_str):
            try:
                price = float(price_str)
                if price > 0:
                    storage_cost_monthly = price * allocated_storage
                    break
            except ValueError:
                continue
    
    # Parse IOPS pricing
    if iops and iops > 0:
        for item in iops_data:
            description = item.get("Description", "").lower()
            usage_type = item.get("UsageType", "").lower()
            price_str = item.get("Price (USD)", "0")
            unit = item.get("Unit", "")
            
            # Look for Single-AZ IOPS (avoid Multi-AZ unless specified)
            is_single_az = "multi-az" not in usage_type and "multi-azcluster" not in usage_type
            
            # Match IOPS pricing for the storage type we're using
            is_matching_storage = False
            if storage_type.lower() == "gp3" and "gp3" in usage_type:
                is_matching_storage = True
            elif storage_type.lower() in ["io1", "io2"] and ("piops" in usage_type or "io1" in usage_type or "io2" in usage_type):
                is_matching_storage = True
            
            if (unit == "IOPS-Mo" and is_single_az and is_matching_storage and
                price_str != "N/A" and price_str):
                try:
                    price = float(price_str)
                    if price > 0:
                        # For gp3 volumes, the first 3,000 IOPS are included for free
                        if storage_type.lower() == "gp3" and iops > 3000:
                            billable_iops = iops - 3000  # Only charge for IOPS above the free baseline
                            iops_cost_monthly = price * billable_iops
                        elif storage_type.lower() == "gp3" and iops <= 3000:
                            iops_cost_monthly = 0  # All IOPS are within the free baseline
                        else:
                            # For io1, io2, and other storage types, charge for all IOPS
                            iops_cost_monthly = price * iops
                        break
                except ValueError:
                    continue
    
    # Parse throughput pricing (for gp3 volumes with provisioned throughput above baseline)
    if storage_throughput and storage_throughput > 125 and storage_type.lower() == "gp3":  # gp3 baseline is 125 MB/s
        provisioned_throughput = storage_throughput - 125  # Only charge for throughput above baseline
        for item in throughput_data:
            usage_type = item.get("UsageType", "")
            price_str = item.get("Price (USD)", "0")
            unit = item.get("Unit", "")
            
            # Look for gp3-throughput usage type (e.g., "aps3-rds:gp3-throughput", "use1-rds:gp3-throughput")
            is_gp3_throughput = "gp3-throughput" in usage_type.lower()
            
            # Look for Single-AZ throughput (avoid Multi-AZ unless specified)
            is_single_az = "multi-az" not in usage_type.lower() and "multi-azcluster" not in usage_type.lower()
            
            if (is_gp3_throughput and is_single_az and price_str != "N/A" and price_str):
                try:
                    price = float(price_str)
                    if price > 0:
                        throughput_cost_monthly = price * provisioned_throughput
                        break
                except ValueError:
                    continue
    
    return {
        "instance": instance_price,  # Already hourly
        "storage": storage_cost_monthly / 730 if storage_cost_monthly > 0 else 0,  # Convert monthly to hourly
        "iops": iops_cost_monthly / 730 if iops_cost_monthly > 0 else 0,  # Convert monthly to hourly
        "throughput": throughput_cost_monthly / 730 if throughput_cost_monthly > 0 else 0,  # Convert monthly to hourly
        "total": instance_price + (storage_cost_monthly / 730) + (iops_cost_monthly / 730) + (throughput_cost_monthly / 730)
    }


def map_engine_name_for_pricing(engine):
    """
    Map RDS engine names to AWS Pricing API engine names.
    """
    engine_mapping = {
        'aurora-mysql': 'Aurora MySQL',
        'aurora-postgresql': 'Aurora PostgreSQL',
        'aurora': 'Aurora MySQL',  # Default Aurora to MySQL
        'mysql': 'MySQL',
        'postgres': 'PostgreSQL',
        'postgresql': 'PostgreSQL',
        'mariadb': 'MariaDB',
        'oracle-ee': 'Oracle',
        'oracle-se2': 'Oracle',
        'sqlserver-ex': 'SQL Server',
        'sqlserver-web': 'SQL Server',
        'sqlserver-se': 'SQL Server',
        'sqlserver-ee': 'SQL Server',
    }
    return engine_mapping.get(engine.lower(), engine)

def fetch_pricing_for_region_engine(region, engine, instances):
    """Fetch pricing data for a specific region/engine combination."""
    pricing_engine = map_engine_name_for_pricing(engine)
    
    # Get unique instance types to filter pricing data
    instance_types = set(inst["DBInstanceClass"] for inst in instances)
    print(f"[INFO] Fetching pricing for {engine} ({pricing_engine}) in {region}, {len(instance_types)} instance types...")
    
    def fetch_data_type(data_type, filters=None):
        """Helper to fetch specific data type with error handling."""
        try:
            if filters is None:
                filters = []
            return get_rds_pricing_data(region=region, engine=pricing_engine, filters=filters)
        except Exception as e:
            print(f"[WARN] Failed to fetch {data_type} for {engine} in {region}: {e}")
            return []
    
    try:
        # Revert to simple parallel approach but with connection pooling
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all 4 API calls simultaneously
            future_instance = executor.submit(fetch_data_type, "instance")
            future_storage = executor.submit(fetch_data_type, "storage", 
                                           [{"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Database Storage"}])
            future_iops = executor.submit(fetch_data_type, "iops",
                                        [{"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Provisioned IOPS"}])
            future_throughput = executor.submit(fetch_data_type, "throughput", [])
            
            # Collect results
            instance_pricing_data = future_instance.result()
            storage_pricing_data = future_storage.result()
            iops_pricing_data = future_iops.result()
            throughput_pricing_data = future_throughput.result()
        
        # Filter results to only relevant instance types to reduce processing time
        if instance_pricing_data:
            original_count = len(instance_pricing_data)
            instance_pricing_data = [
                item for item in instance_pricing_data 
                if item.get("InstanceType", "") in instance_types or not item.get("InstanceType")
            ]
            print(f"[INFO] Filtered instance records: {len(instance_pricing_data)}/{original_count}")
        
        # Filter throughput data
        throughput_pricing_data = [
            item for item in throughput_pricing_data 
            if 'throughput' in item.get('UsageType', '').lower()
        ]
        
        if not instance_pricing_data:
            print(f"[WARN] No instance pricing data found for {engine} ({pricing_engine}) in {region}")
            return {(inst["DBInstanceIdentifier"], region, engine): None for inst in instances}
        
        # Process each instance in this group
        result_prices = {}
        for inst in instances:
            instance_class = inst["DBInstanceClass"]
            instance_id = inst["DBInstanceIdentifier"]  # Add instance identifier
            storage_type = inst.get("StorageType", "gp3")
            allocated_storage = inst.get("AllocatedStorage", 0)
            iops = inst.get("Iops", 0)
            storage_throughput = inst.get("StorageThroughput", 0)
            
            # Parse pricing components using separate datasets
            price_breakdown = parse_pricing_components_v2(
                instance_pricing_data, storage_pricing_data, iops_pricing_data, throughput_pricing_data,
                instance_class, storage_type, allocated_storage, iops, storage_throughput
            )
            
            # Use instance identifier as key to prevent overwriting instances with same class
            result_prices[(instance_id, region, engine)] = price_breakdown
            
            if price_breakdown["total"] == 0:
                print(f"[WARN] No price found for {instance_id} ({instance_class}) in {region} (engine: {engine})")
        
        return result_prices
                
    except Exception as e:
        print(f"[ERROR] Pricing API failed for {engine} in {region}: {e}")
        return {(inst["DBInstanceIdentifier"], region, engine): None for inst in instances}


def fetch_rds_pricing(rds_instances, nocache=False):
    """Fetch live on-demand hourly pricing for each RDS instance type with caching and parallel execution."""
    # Try to load from cache first (unless nocache is specified)
    cached_prices = load_cached_pricing(nocache=nocache)
    if cached_prices is not None:
        return cached_prices

    # Fetch fresh data from AWS
    print("[INFO] Fetching fresh pricing data from AWS...")
    prices = {}
    
    # Group instances by region and engine to minimize API calls
    region_engine_groups = {}
    for inst in rds_instances:
        region = inst["Region"]
        engine = inst["Engine"]
        key = (region, engine)
        if key not in region_engine_groups:
            region_engine_groups[key] = []
        region_engine_groups[key].append(inst)
    
    print(f"[INFO] Processing {len(region_engine_groups)} unique region/engine combinations in parallel...")
    
    # Use ThreadPoolExecutor to parallelize region/engine combinations
    with ThreadPoolExecutor(max_workers=min(8, len(region_engine_groups))) as executor:
        # Submit all region/engine combinations for parallel processing
        future_to_key = {
            executor.submit(fetch_pricing_for_region_engine, region, engine, instances): (region, engine)
            for (region, engine), instances in region_engine_groups.items()
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_key):
            region, engine = future_to_key[future]
            try:
                region_prices = future.result()
                prices.update(region_prices)
            except Exception as e:
                print(f"[ERROR] Failed to process {engine} in {region}: {e}")
                # Add None entries for failed instances
                instances = region_engine_groups[(region, engine)]
                for inst in instances:
                    prices[(inst["DBInstanceIdentifier"], region, engine)] = None

    # Save to cache
    save_cached_pricing(prices)
    return prices
