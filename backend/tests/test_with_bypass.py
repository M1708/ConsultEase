"""
Test with authentication bypass for development
"""
import requests
import json
import time

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USER_ID = "302730ff-2aad-424e-a1ad-10126efaa4d6"

def test_api_endpoint(message: str, description: str):
    """Test a single API endpoint with test bypass"""
    print(f"\n=== {description} ===")
    print(f"Message: '{message}'")
    
    start_time = time.time()
    
    try:
        # Use test bypass header
        headers = {
            "X-Test-Mode": "true",
            "X-Test-User-ID": TEST_USER_ID
        }
        
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
            response_text = data.get('response', 'No response')
            print(f"Response: {response_text[:500]}...")
            if len(response_text) > 500:
                print("... (truncated)")
            
            # Analyze the response for specific issues
            analyze_response(message, response_text, description)
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

def analyze_response(message: str, response: str, description: str):
    """Analyze the response for specific issues mentioned in feedback"""
    response_lower = response.lower()
    
    if "hi" in message.lower():
        if "abc@abc.com" not in response_lower and "abc" not in response_lower:
            print("❌ ISSUE: Greeting does not include username/email")
        else:
            print("✅ Greeting includes user information")
    
    elif "clients with their contracts" in message.lower():
        if "contract" not in response_lower:
            print("❌ ISSUE: Response mentions clients but no contracts")
        elif "contract_id" in response_lower or "contract id" in response_lower:
            print("✅ Response includes contract details")
        else:
            print("⚠️  Response mentions contracts but may lack details")
    
    elif "contracts for" in message.lower():
        if "contract" not in response_lower:
            print("❌ ISSUE: No contract information in response")
        elif "create" in response_lower and "contract" in response_lower:
            print("❌ ISSUE: Asking to create contracts instead of showing existing ones")
        else:
            print("✅ Shows contract information")
    
    elif "all contracts" in message.lower():
        if "provide the name" in response_lower or "which client" in response_lower:
            print("❌ ISSUE: Asking for client name instead of showing all contracts")
        elif "contract" in response_lower:
            print("✅ Shows contract information")
        else:
            print("❌ ISSUE: No contract information provided")

def main():
    """Run all API tests"""
    print("🧪 Testing FastAPI endpoints with test bypass...")
    print("⚠️  Note: This test will fail until test bypass is implemented")
    
    # Test scenarios from user feedback
    test_cases = [
        ("hi", "Test 1: Greeting (should include username)"),
        ("show me all clients with their contracts", "Test 2: All clients with contracts (should show BOTH client AND contract details)"),
        ("show me contracts for TechCorp", "Test 3: Specific client contracts (should show contract details, not just client info)"),
        ("show me all contracts", "Test 4: All contracts (should show all contracts, not ask for client name)"),
    ]
    
    for message, description in test_cases:
        test_api_endpoint(message, description)
        time.sleep(1)  # Brief pause between requests
    
    print("\n🎉 All API tests completed!")

if __name__ == "__main__":
    main()
