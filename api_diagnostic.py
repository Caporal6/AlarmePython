#!/usr/bin/env python3
# api_diagnostic.py - Tool to diagnose API endpoint issues

import requests
import sys
import json
import argparse

def test_endpoint(base_url, endpoint, method='GET', data=None):
    """Test a specific endpoint with the given method and data"""
    url = f"{base_url}{endpoint}"
    print(f"\n----- Testing {method} {url} -----")
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        if method == 'GET':
            response = requests.get(url, timeout=5)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers, timeout=5)
        else:
            print(f"Unsupported method: {method}")
            return False
            
        print(f"Status: {response.status_code} {response.reason}")
        
        # Try to parse response as JSON
        try:
            json_response = response.json()
            print("Response JSON:")
            print(json.dumps(json_response, indent=2))
        except:
            print("Response (not JSON):")
            print(response.text[:200] + ('...' if len(response.text) > 200 else ''))
            
        return response.ok
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Test API endpoints')
    parser.add_argument('--host', default='http://localhost:5000', help='Base URL for API')
    parser.add_argument('--test-all', action='store_true', help='Test all endpoints')
    parser.add_argument('--endpoint', help='Specific endpoint to test')
    parser.add_argument('--method', default='GET', help='HTTP method (GET or POST)')
    
    args = parser.parse_args()
    
    base_url = args.host
    
    # Test if server is running
    try:
        response = requests.get(f"{base_url}/", timeout=2)
        print(f"Server is running at {base_url}")
    except Exception as e:
        print(f"Error connecting to server at {base_url}: {str(e)}")
        sys.exit(1)
    
    if args.endpoint:
        # Test specific endpoint
        data = None
        if args.method == 'POST':
            if args.endpoint == '/test_hardware' or args.endpoint == '/test_hardware_fixed':
                data = {'component': 'led', 'action': 'on'}
            else:
                data = {'test': 'data'}
                
        test_endpoint(base_url, args.endpoint, args.method, data)
    elif args.test_all:
        # Test all relevant endpoints
        endpoints = [
            {'url': '/hardware_status', 'method': 'GET'},
            {'url': '/sensor_data', 'method': 'GET'},
            {'url': '/test_hardware', 'method': 'POST', 'data': {'component': 'led', 'action': 'on'}},
            {'url': '/test_hardware_fixed', 'method': 'POST', 'data': {'component': 'led', 'action': 'on'}},
            {'url': '/simple_hardware_test', 'method': 'POST', 'data': {'component': 'led', 'action': 'on'}}
        ]
        
        results = []
        for endpoint in endpoints:
            url = endpoint['url']
            method = endpoint.get('method', 'GET')
            data = endpoint.get('data')
            
            success = test_endpoint(base_url, url, method, data)
            results.append({
                'endpoint': url,
                'method': method,
                'success': success
            })
        
        # Summary
        print("\n----- Summary -----")
        for result in results:
            status = '✓' if result['success'] else '✗'
            print(f"{status} {result['method']} {result['endpoint']}")
    else:
        print("Please specify --endpoint or --test-all")

if __name__ == "__main__":
    main()
