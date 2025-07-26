#!/usr/bin/env python3
"""
Testing Script for Gumroad Backend API
Run this to test all your API endpoints
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"  # Change to your deployed URL when ready
TEST_EMAIL = "test@example.com"  # Change to actual email for testing
TEST_PRODUCT_ID = "qIJg4n61wF3gMgV1-St1AQ=="  # Your Quotex extension product ID

def print_separator(title):
    """Print a nice separator for test sections"""
    print("\n" + "="*60)
    print(f"🧪 {title}")
    print("="*60)

def make_request(method, endpoint, data=None):
    """Make HTTP request and return response"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == 'GET':
            response = requests.get(url)
        elif method.upper() == 'POST':
            response = requests.post(url, json=data, headers={'Content-Type': 'application/json'})
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        print(f"📡 {method.upper()} {endpoint}")
        print(f"📊 Status Code: {response.status_code}")
        
        try:
            result = response.json()
            print(f"📋 Response: {json.dumps(result, indent=2)}")
            return response.status_code, result
        except:
            print(f"📋 Response: {response.text}")
            return response.status_code, response.text
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return None, str(e)

def test_health_check():
    """Test basic health check"""
    print_separator("Health Check")
    status_code, response = make_request('GET', '/health')
    
    if status_code == 200:
        print("✅ Health check passed!")
    else:
        print("❌ Health check failed!")
    
    return status_code == 200

def test_admin_status():
    """Test admin status endpoint"""
    print_separator("Admin Status")
    status_code, response = make_request('GET', '/admin/status')
    
    if status_code == 200:
        if isinstance(response, dict):
            api_working = response.get('gumroad_api_working', False)
            has_token = response.get('config', {}).get('has_access_token', False)
            
            print(f"✅ API Connection: {'Working' if api_working else 'Failed'}")
            print(f"✅ Access Token: {'Configured' if has_token else 'Missing'}")
            
            if api_working and has_token:
                print("🎉 Backend is properly configured!")
                return True
            else:
                print("⚠️ Backend needs configuration!")
                return False
        else:
            print("❌ Unexpected response format!")
            return False
    else:
        print("❌ Admin status check failed!")
        return False

def test_get_products():
    """Test getting products list"""
    print_separator("Get Products List")
    status_code, response = make_request('GET', '/admin/products')
    
    if status_code == 200 and isinstance(response, dict):
        products = response.get('products', [])
        print(f"📦 Found {len(products)} products:")
        
        for i, product in enumerate(products, 1):
            print(f"   {i}. {product.get('name')} (ID: {product.get('id')})")
            print(f"      URL: {product.get('url')}")
            print(f"      Price: {product.get('price')} {product.get('currency')}")
            print(f"      Sales: {product.get('sales_count')}")
            print(f"      Subscription: {product.get('is_subscription')}")
            print()
        
        # Check if our test product ID exists
        product_ids = [p.get('id') for p in products]
        if TEST_PRODUCT_ID in product_ids:
            print(f"✅ Test product ID '{TEST_PRODUCT_ID}' found in products list!")
        else:
            print(f"⚠️ Test product ID '{TEST_PRODUCT_ID}' not found in products list!")
            print(f"Available product IDs: {product_ids}")
        
        return True
    else:
        print("❌ Failed to get products list!")
        return False

def test_subscription_check_valid():
    """Test subscription check with valid product ID"""
    print_separator(f"Subscription Check - Valid Product ({TEST_PRODUCT_ID})")
    
    data = {
        "email": TEST_EMAIL,
        "product_id": TEST_PRODUCT_ID
    }
    
    status_code, response = make_request('POST', '/check-subscription', data)
    
    if status_code == 200 and isinstance(response, dict):
        active = response.get('active', False)
        email = response.get('email')
        product_id = response.get('product_id')
        message = response.get('message')
        
        print(f"📧 Email: {email}")
        print(f"📦 Product ID: {product_id}")
        print(f"✅ Active: {active}")
        print(f"💬 Message: {message}")
        
        if 'api_error' in response:
            print(f"⚠️ API Error: {response['api_error']}")
            return False
        
        print("✅ Subscription check completed successfully!")
        return True
    else:
        print("❌ Subscription check failed!")
        return False

def test_subscription_check_invalid():
    """Test subscription check with invalid product ID"""
    print_separator("Subscription Check - Invalid Product")
    
    data = {
        "email": TEST_EMAIL,
        "product_id": "invalid_product_123"
    }
    
    status_code, response = make_request('POST', '/check-subscription', data)
    
    if status_code == 200:
        print("✅ API handled invalid product ID gracefully!")
        return True
    else:
        print("❌ API should handle invalid product IDs!")
        return False

def test_subscription_check_missing_data():
    """Test subscription check with missing data"""
    print_separator("Subscription Check - Missing Data")
    
    # Test missing email
    print("📧 Testing missing email...")
    data = {"product_id": TEST_PRODUCT_ID}
    status_code, response = make_request('POST', '/check-subscription', data)
    
    if status_code == 400:
        print("✅ Correctly rejected missing email!")
    else:
        print("❌ Should reject missing email!")
        return False
    
    # Test missing product_id
    print("\n📦 Testing missing product_id...")
    data = {"email": TEST_EMAIL}
    status_code, response = make_request('POST', '/check-subscription', data)
    
    if status_code == 400:
        print("✅ Correctly rejected missing product_id!")
        return True
    else:
        print("❌ Should reject missing product_id!")
        return False

def test_purchase_url():
    """Test getting purchase URL"""
    print_separator("Get Purchase URL")
    
    data = {"product_id": TEST_PRODUCT_ID}
    status_code, response = make_request('POST', '/get-purchase-url', data)
    
    if status_code == 200 and isinstance(response, dict):
        purchase_url = response.get('purchase_url')
        product_id = response.get('product_id')
        
        print(f"🛒 Purchase URL: {purchase_url}")
        print(f"📦 Product ID: {product_id}")
        
        expected_url = f"https://gumroad.com/l/{TEST_PRODUCT_ID}"
        if purchase_url == expected_url:
            print("✅ Purchase URL is correct!")
            return True
        else:
            print(f"❌ Expected: {expected_url}")
            print(f"❌ Got: {purchase_url}")
            return False
    else:
        print("❌ Failed to get purchase URL!")
        return False

def test_cache_functionality():
    """Test caching functionality"""
    print_separator("Cache Functionality")
    
    # Clear cache first
    print("🧹 Clearing cache...")
    status_code, response = make_request('POST', '/admin/clear-cache')
    
    if status_code != 200:
        print("❌ Failed to clear cache!")
        return False
    
    # Make first request (should hit API)
    print("\n📡 Making first request (should hit Gumroad API)...")
    data = {"email": TEST_EMAIL, "product_id": TEST_PRODUCT_ID}
    start_time = time.time()
    status_code, response = make_request('POST', '/check-subscription', data)
    first_request_time = time.time() - start_time
    
    if status_code != 200:
        print("❌ First request failed!")
        return False
    
    cached_first = response.get('cached', False)
    print(f"📊 First request - Cached: {cached_first}, Time: {first_request_time:.2f}s")
    
    # Make second request immediately (should use cache)
    print("\n📡 Making second request (should use cache)...")
    start_time = time.time()
    status_code, response = make_request('POST', '/check-subscription', data)
    second_request_time = time.time() - start_time
    
    if status_code != 200:
        print("❌ Second request failed!")
        return False
    
    cached_second = response.get('cached', False)
    print(f"📊 Second request - Cached: {cached_second}, Time: {second_request_time:.2f}s")
    
    if cached_second and second_request_time < first_request_time:
        print("✅ Caching is working properly!")
        return True
    else:
        print("⚠️ Caching might not be working as expected")
        return False

def test_comprehensive_user_flow():
    """Test complete user flow"""
    print_separator("Complete User Flow Test")
    
    # Step 1: User gets purchase URL
    print("🛒 Step 1: Getting purchase URL...")
    data = {"product_id": TEST_PRODUCT_ID}
    status_code, response = make_request('POST', '/get-purchase-url', data)
    
    if status_code != 200:
        print("❌ Failed to get purchase URL!")
        return False
    
    purchase_url = response.get('purchase_url')
    print(f"✅ Purchase URL: {purchase_url}")
    
    # Step 2: Check subscription (should be inactive for test email)
    print("\n🔍 Step 2: Checking subscription status...")
    data = {"email": TEST_EMAIL, "product_id": TEST_PRODUCT_ID}
    status_code, response = make_request('POST', '/check-subscription', data)
    
    if status_code != 200:
        print("❌ Failed to check subscription!")
        return False
    
    active = response.get('active', False)
    total_sales = response.get('total_sales', 0)
    
    print(f"✅ Subscription Active: {active}")
    print(f"✅ Total Sales: {total_sales}")
    
    if not active:
        print("💡 This is expected for a test email that hasn't purchased")
    
    print("🎉 Complete user flow test passed!")
    return True

def run_all_tests():
    """Run all tests"""
    print("🚀 Starting Gumroad Backend API Tests")
    print(f"🎯 Target URL: {BASE_URL}")
    print(f"📧 Test Email: {TEST_EMAIL}")
    print(f"📦 Test Product ID: {TEST_PRODUCT_ID}")
    
    tests = [
        # ("Health Check", test_health_check),
        # ("Admin Status", test_admin_status),
        # ("Get Products", test_get_products),
        ("Valid Subscription Check", test_subscription_check_valid),
        # ("Invalid Product Check", test_subscription_check_invalid),
        # ("Missing Data Check", test_subscription_check_missing_data),
        # ("Purchase URL", test_purchase_url),
        # ("Cache Functionality", test_cache_functionality),
        # ("Complete User Flow", test_comprehensive_user_flow)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print_separator("TEST RESULTS SUMMARY")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n📊 OVERALL RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your API is working perfectly!")
    elif passed > total // 2:
        print("⚠️ Most tests passed, but some issues need attention")
    else:
        print("❌ Multiple tests failed, please check your configuration")
    
    return passed == total

if __name__ == "__main__":
    # You can modify these settings
    print("⚙️ Configuration:")
    print(f"   BASE_URL = {BASE_URL}")
    print(f"   TEST_EMAIL = {TEST_EMAIL}")
    print(f"   TEST_PRODUCT_ID = {TEST_PRODUCT_ID}")
    print("\n💡 To test with different settings, modify the variables at the top of this file")
    
    input("\n⏯️ Press Enter to start testing...")
    
    success = run_all_tests()
    
    if success:
        print("\n🚀 Ready for production! Your backend is working correctly.")
    else:
        print("\n🔧 Please fix the issues above before deploying to production.")