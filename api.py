#!/usr/bin/env python3
"""
Gumroad Subscription Backend - Python Flask (Dynamic Product Support)
For Multiple Extensions/Products
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import time
from datetime import datetime, timedelta
import os
from typing import Dict, Any, Optional

app = Flask(__name__)
CORS(app)  # Enable CORS for Chrome extension

# Your Gumroad credentials (Product ID now comes from API calls)
GUMROAD_CONFIG = {
    'APPLICATION_ID': '_yxTmED28YvCwMpE7q3iNDLlxmxXzGgniY_Rg7sS4m0',
    'APPLICATION_SECRET': 'L-URYhN27ltnmJem8witjaNTIT4-gqM1CYavjbi7dmc',
    'ACCESS_TOKEN': 'X7WpL7I-LGq2vazbkSYyQStKIjJcj7nHGKGbWpPJ_yg'
}

# Cache for subscription status (to avoid too many API calls)
# Cache key format: "email:product_id"
subscription_cache = {}
CACHE_DURATION = 300  # 5 minutes in seconds

class GumroadAPI:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = 'https://api.gumroad.com/v2'
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    def get_sales(self, page: int = 1, product_id: str = None) -> Dict[str, Any]:
        """Get sales from Gumroad API, optionally filtered by product"""
        try:
            url = f'{self.base_url}/sales'
            params = {'page': page}
            
            if product_id:
                params['product_id'] = product_id
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching sales: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_user_info(self) -> Dict[str, Any]:
        """Get user info to test API connection"""
        try:
            url = f'{self.base_url}/user'
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching user info: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_products(self) -> Dict[str, Any]:
        """Get all products from Gumroad"""
        try:
            url = f'{self.base_url}/products'
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching products: {e}")
            return {'success': False, 'error': str(e)}

def check_gumroad_subscription(email: str, product_id: str) -> Dict[str, Any]:
    """Check if user has active subscription for specific product via Gumroad API"""
    
    # Check cache first
    cache_key = f"{email.lower()}:{product_id}"
    current_time = time.time()
    
    if cache_key in subscription_cache:
        cached_data = subscription_cache[cache_key]
        if current_time - cached_data['timestamp'] < CACHE_DURATION:
            print(f"Returning cached result for {email} - {product_id}")
            return cached_data['data']
    
    # Initialize Gumroad API
    gumroad_api = GumroadAPI(GUMROAD_CONFIG['ACCESS_TOKEN'])
    
    try:
        # Get sales data for specific product
        sales_data = gumroad_api.get_sales(product_id=product_id)
        
        if not sales_data.get('success', True):
            raise Exception(sales_data.get('message', 'API call failed'))
        
        sales = sales_data.get('sales', [])
        
        # Filter sales for this email
        user_sales = [
            sale for sale in sales
            if sale.get('email', '').lower() == email.lower()
        ]
        
        # Check for active subscription
        has_active_subscription = False
        latest_sale = None
        subscription_details = []
        
        for sale in user_sales:
            sale_info = {
                'sale_id': sale.get('sale_id'),
                'created_at': sale.get('created_at'),
                'price': sale.get('price'),
                'refunded': sale.get('refunded', False),
                'disputed': sale.get('disputed', False),
                'subscription_id': sale.get('subscription_id')
            }
            subscription_details.append(sale_info)
            
            # Check if it's a subscription and not refunded
            if (sale.get('subscription_id') and 
                not sale.get('refunded', False) and 
                not sale.get('disputed', False)):
                has_active_subscription = True
                if not latest_sale or sale.get('created_at', '') > latest_sale.get('created_at', ''):
                    latest_sale = sale
        
        result = {
            'active': has_active_subscription,
            'email': email,
            'product_id': product_id,
            'total_sales': len(user_sales),
            'last_purchase': latest_sale.get('created_at') if latest_sale else None,
            'subscription_id': latest_sale.get('subscription_id') if latest_sale else None,
            'last_price': latest_sale.get('price') if latest_sale else None,
            'subscription_details': subscription_details,
            'checked_at': datetime.now().isoformat()
        }
        
        # Cache the result
        subscription_cache[cache_key] = {
            'data': result,
            'timestamp': current_time
        }
        
        return result
        
    except Exception as e:
        print(f"Error checking subscription for {email} - {product_id}: {e}")
        return {
            'active': False,
            'email': email,
            'product_id': product_id,
            'error': str(e),
            'checked_at': datetime.now().isoformat()
        }

@app.route('/check-subscription', methods=['POST'])
def check_subscription():
    """API endpoint for extension to check subscription status"""
    
    try:
        data = request.get_json()
        email = data.get('email')
        product_id = data.get('product_id')
        
        if not email:
            return jsonify({
                'active': False,
                'error': 'Email is required'
            }), 400
        
        if not product_id:
            return jsonify({
                'active': False,
                'error': 'Product ID is required'
            }), 400
        
        if not GUMROAD_CONFIG['ACCESS_TOKEN']:
            return jsonify({
                'active': False,
                'error': 'Gumroad access token not configured'
            }), 500
        
        # Check subscription status
        subscription_status = check_gumroad_subscription(email, product_id)
        
        response_data = {
            'active': subscription_status['active'],
            'email': subscription_status['email'],
            'product_id': subscription_status['product_id'],
            'message': 'Active subscription found' if subscription_status['active'] else 'No active subscription found',
            'last_purchase': subscription_status.get('last_purchase'),
            'last_price': subscription_status.get('last_price'),
            'total_sales': subscription_status.get('total_sales', 0),
            'subscription_id': subscription_status.get('subscription_id'),
            'subscription_details': subscription_status.get('subscription_details', []),
            'cached': f"{email.lower()}:{product_id}" in subscription_cache,
            'checked_at': subscription_status.get('checked_at')
        }
        
        if 'error' in subscription_status:
            response_data['api_error'] = subscription_status['error']
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Subscription check error: {e}")
        return jsonify({
            'active': False,
            'error': f'Failed to check subscription: {str(e)}',
            'email': data.get('email', 'unknown') if 'data' in locals() else 'unknown',
            'product_id': data.get('product_id', 'unknown') if 'data' in locals() else 'unknown'
        }), 500

@app.route('/get-purchase-url', methods=['POST'])
def get_purchase_url():
    """Get Gumroad purchase URL for specific product"""
    
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        
        if not product_id:
            return jsonify({
                'error': 'Product ID is required'
            }), 400
        
        gumroad_url = f'https://gumroad.com/l/{product_id}'
        
        return jsonify({
            'purchase_url': gumroad_url,
            'product_id': product_id,
            'message': 'Subscribe with credit card on Gumroad'
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to generate purchase URL: {str(e)}'
        }), 500

@app.route('/admin/status', methods=['GET'])
def admin_status():
    """Admin endpoint to check system status"""
    
    try:
        # Test API connection
        gumroad_api = GumroadAPI(GUMROAD_CONFIG['ACCESS_TOKEN'])
        user_info = gumroad_api.get_user_info()
        api_working = user_info.get('success', True)
        
        # Get products list
        products_info = gumroad_api.get_products()
        
        cache_size = len(subscription_cache)
        
        # Clean expired cache entries
        current_time = time.time()
        expired_keys = [
            key for key, value in subscription_cache.items()
            if current_time - value['timestamp'] > CACHE_DURATION
        ]
        
        for key in expired_keys:
            del subscription_cache[key]
        
        return jsonify({
            'status': 'OK',
            'timestamp': datetime.now().isoformat(),
            'gumroad_api_working': api_working,
            'cache_entries': cache_size,
            'expired_cache_cleaned': len(expired_keys),
            'config': {
                'has_access_token': bool(GUMROAD_CONFIG['ACCESS_TOKEN']),
                'application_id': GUMROAD_CONFIG['APPLICATION_ID']
            },
            'user_info': user_info if api_working else None,
            'products': products_info.get('products', []) if products_info.get('success', True) else []
        })
        
    except Exception as e:
        return jsonify({
            'status': 'ERROR',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/admin/products', methods=['GET'])
def get_products():
    """Get all products from Gumroad"""
    
    try:
        gumroad_api = GumroadAPI(GUMROAD_CONFIG['ACCESS_TOKEN'])
        products_data = gumroad_api.get_products()
        
        if not products_data.get('success', True):
            return jsonify({
                'error': products_data.get('message', 'Failed to fetch products')
            }), 500
        
        products = products_data.get('products', [])
        
        # Format product information
        formatted_products = []
        for product in products:
            formatted_products.append({
                'id': product.get('id'),
                'name': product.get('name'),
                'url': product.get('short_url'),
                'price': product.get('price'),
                'currency': product.get('currency'),
                'sales_count': product.get('sales_count', 0),
                'is_subscription': product.get('subscription_duration') is not None
            })
        
        return jsonify({
            'products': formatted_products,
            'total': len(formatted_products),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/admin/clear-cache', methods=['POST'])
def clear_cache():
    """Clear subscription cache (for testing)"""
    
    cache_size = len(subscription_cache)
    subscription_cache.clear()
    
    return jsonify({
        'message': 'Cache cleared successfully',
        'entries_cleared': cache_size,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/admin/subscribers', methods=['GET'])
def get_subscribers():
    """Get list of cached subscribers (for debugging)"""
    
    current_time = time.time()
    subscribers = []
    
    for cache_key, cache_data in subscription_cache.items():
        subscriber_info = cache_data['data'].copy()
        subscriber_info['cache_key'] = cache_key
        subscriber_info['cache_age_seconds'] = int(current_time - cache_data['timestamp'])
        subscriber_info['cache_expired'] = (current_time - cache_data['timestamp']) > CACHE_DURATION
        subscribers.append(subscriber_info)
    
    return jsonify({
        'total_cached': len(subscribers),
        'active_subscribers': len([s for s in subscribers if s.get('active', False)]),
        'subscribers': subscribers,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    
    return jsonify({
        'status': 'OK',
        'timestamp': datetime.now().isoformat(),
        'cache_size': len(subscription_cache),
        'service': 'Multi-Product Gumroad Backend'
    })

@app.route('/', methods=['GET'])
def home():
    """Root endpoint with basic info"""
    
    return jsonify({
        'service': 'Multi-Product Gumroad Subscription Backend',
        'status': 'Running',
        'version': '2.0.0',
        'features': [
            'Dynamic product ID support',
            'Multi-product subscription checking',
            'Intelligent caching',
            'Comprehensive admin tools'
        ],
        'endpoints': {
            'check_subscription': '/check-subscription [POST] - Requires: email, product_id',
            'get_purchase_url': '/get-purchase-url [POST] - Requires: product_id',
            'health_check': '/health [GET]',
            'admin_status': '/admin/status [GET]',
            'admin_products': '/admin/products [GET]'
        },
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 Starting Multi-Product Gumroad Backend")
    print(f"📊 Admin status: http://localhost:5000/admin/status")
    print(f"📦 Products list: http://localhost:5000/admin/products")
    print(f"💳 Features:")
    print(f"   ✅ Dynamic product ID support")
    print(f"   ✅ Multi-product subscription checking")
    print(f"   ✅ Intelligent caching")
    print(f"   ✅ Comprehensive testing endpoints")
    
    # Use environment variables in production
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug)