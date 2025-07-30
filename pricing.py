import boto3
import json
import os
import time
from datetime import datetime, timedelta

# Cache configuration
CACHE_FILE = "/tmp/rds_pricing_cache.json"
CACHE_DURATION_HOURS = 24  # Cache for 24 hours

def tuple_to_key(tuple_key):
    """Convert tuple key to string for JSON serialization."""
    return f"{tuple_key[0]}|{tuple_key[1]}|{tuple_key[2]}"

def key_to_tuple(string_key):
    """Convert string key back to tuple for internal use."""
    parts = string_key.split("|")
    return (parts[0], parts[1], parts[2])

def load_cached_pricing():
    """Load pricing data from cache if it exists and is valid."""
    try:
        if not os.path.exists(CACHE_FILE):
            return None
        
        with open(CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
        
        # Check if cache is still valid
        cache_time = datetime.fromisoformat(cache_data['timestamp'])
        if datetime.now() - cache_time > timedelta(hours=CACHE_DURATION_HOURS):
            print("[INFO] Pricing cache expired, fetching fresh data...")
            return None
        
        # Convert string keys back to tuples
        prices = {}
        for string_key, price in cache_data['prices'].items():
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
            'timestamp': datetime.now().isoformat(),
            'prices': serializable_prices
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
        print("[INFO] Pricing data cached successfully.")
    except Exception as e:
        print(f"[WARN] Error saving cache: {e}")

def fetch_rds_pricing(rds_instances):
    """Fetch live on-demand hourly pricing for each RDS instance type with caching."""
    # Try to load from cache first
    cached_prices = load_cached_pricing()
    if cached_prices is not None:
        return cached_prices
    
    # Fetch fresh data from AWS
    print("[INFO] Fetching fresh pricing data from AWS...")
    pricing = boto3.client('pricing', region_name='us-east-1')
    prices = {}
    
    for inst in rds_instances:
        instance_class = inst['DBInstanceClass']
        region = inst['Region']
        engine = inst['Engine']
        # Try with minimal filters first
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_class},
            {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': region},
        ]
        # Optionally add engine filter if you want
        # filters.append({'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': engine})
        try:
            resp = pricing.get_products(
                ServiceCode='AmazonRDS',
                Filters=filters,
                MaxResults=5
            )
            price = None
            for p in resp['PriceList']:
                data = json.loads(p)
                terms = data.get('terms', {}).get('OnDemand', {})
                for term in terms.values():
                    for price_dim in term['priceDimensions'].values():
                        price_str = price_dim['pricePerUnit'].get('USD')
                        if price_str:
                            price = float(price_str)
                            break
                    if price is not None:
                        break
                if price is not None:
                    break
            prices[(instance_class, region, engine)] = price
            if price is None:
                print(f"[WARN] No price found for {instance_class} in {region} (engine: {engine})")
        except Exception as e:
            print(f"[ERROR] Pricing API failed for {instance_class} in {region}: {e}")
            prices[(instance_class, region, engine)] = None
    
    # Save to cache
    save_cached_pricing(prices)
    return prices