"""
Test the actual FastAPI endpoints to validate the fixes
"""
import requests
import json
import time

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_EMAIL = "abc@abc.com"
TEST_PASSWORD = "password123"

def get_auth_token():
    """Get a valid JWT token by logging in"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            user_info = data.get("user", {})
            print(f"✅ Authentication successful for user: {user_info.get('email', 'Unknown')}")
            return token
        else:
            print(f"❌ Authentication failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return None

def test_api_endpoint(message: str, description: str, auth_token: str):
    """Test a single API endpoint"""
    print(f"\n=== {description} ===")
    print(f"Message: '{message}'")
    
    start_time = time.time()
    
    try:
        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        
        response = requests.post(
            f"{BASE_URL}/api/chat/message",
            json={"message": message},
            headers=headers,
            timeout=30
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"Status: {response.status_code}")
        print(f"Processing time: {processing_time:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Agent: {data.get('agent', 'Unknown')}")
            print(f"Response: {data.get('response', 'No response')[:500]}...")
            if len(data.get('response', '')) > 500:
                print("... (truncated)")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

def main():
    """Run all API tests"""
    print("🧪 Testing actual FastAPI endpoints...")
    
    # Get authentication token
    print("🔐 Getting authentication token...")
    auth_token = get_auth_token()
    
    if not auth_token:
        print("❌ Cannot proceed without valid authentication token")
        return
    
    # Test scenarios from user feedback
    test_cases = [
        ("hi", "Test 1: Greeting (should include username)"),
        ("show me all clients with their contracts", "Test 2: All clients with contracts (should show BOTH client AND contract details)"),
        ("show me contracts for TechCorp", "Test 3: Specific client contracts (should show contract details, not just client info)"),
        ("show me all contracts", "Test 4: All contracts (should show all contracts, not ask for client name)"),
    ]
    
    for message, description in test_cases:
        test_api_endpoint(message, description, auth_token)
        time.sleep(1)  # Brief pause between requests
    
    print("\n🎉 All API tests completed!")

if __name__ == "__main__":
    main()
