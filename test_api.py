import requests
import json

BASE_URL = "http://localhost:5000"  # Adjust this to your server address

def test_endpoint(url, method="GET", data=None):
    print(f"\nTesting {method} {url}")
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{url}")
        else:  # POST
            response = requests.post(
                f"{BASE_URL}{url}", 
                json=data,
                headers={"Content-Type": "application/json"}
            )
        
        print(f"Status: {response.status_code} {response.reason}")
        print("Response:", response.text[:200])
        
        return response.status_code, response.text
    except Exception as e:
        print(f"Error: {e}")
        return None, str(e)

# Test endpoints
print("=== TESTING API ENDPOINTS ===")

# Test simple GET endpoints
test_endpoint("/")
test_endpoint("/hardware_status")
test_endpoint("/sensor_data")

# Test hardware endpoints
test_data = {"component": "led", "action": "on"}
test_endpoint("/test_hardware", "POST", test_data)
test_endpoint("/test_hardware_fixed", "POST", test_data)
test_endpoint("/simple_test", "POST", test_data)