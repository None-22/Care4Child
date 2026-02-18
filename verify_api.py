import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("🚀 Starting API Verification...")
    
    # 1. Get Auth Token
    print(f"\n1. Authenticating as 'admin'...")
    try:
        response = requests.post(f"{BASE_URL}/api/auth/token/", data={
            "username": "admin",
            "password": "admin123"
        })
        
        if response.status_code == 200:
            token = response.json().get('token')
            print(f"✅ Success! Token received: {token[:10]}...")
        else:
            print(f"❌ Failed to get token. Status: {response.status_code}")
            print(response.text)
            return
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is 'python manage.py runserver' running?")
        return

    # 2. Test Children Endpoint (with new fields)
    print(f"\n2. Fetching Children (Checking for birth location fields)...")
    headers = {
        "Authorization": f"Token {token}",
        "Accept": "application/json"
    }
    
    response = requests.get(f"{BASE_URL}/api/children/", headers=headers)
    
    if response.status_code == 200:
        children = response.json()
        print(f"✅ Success! Found {len(children)} children.")
        
        if len(children) > 0:
            child_summary = children[0]
            child_id = child_summary.get('id')
            print(f"\n   Found Child ID: {child_id}. Fetching Details...")
            
            # 3. Fetch Detail
            detail_resp = requests.get(f"{BASE_URL}/api/children/{child_id}/", headers=headers)
            if detail_resp.status_code != 200:
                 print(f"❌ Failed to fetch child detail. Status: {detail_resp.status_code}")
                 print(detail_resp.text)
                 return
            
            child = detail_resp.json()
            print(f"   Name: {child.get('full_name')}")
            
            # Verify the NEW fields are present
            print("\n   Checking New Birth Location Fields in Detail View:")
            
            # Checking keys in response
            required_fields = ['birth_governorate', 'birth_directorate', 'birth_health_center', 'place_of_birth_detail']
            missing = [f for f in required_fields if f not in child]
            
            if not missing:
                print("   ✅ All birth location fields are present in the response.")
                print(f"   - Birth Gov: {child.get('birth_governorate')}")
                print(f"   - Birth Dir: {child.get('birth_directorate')}")
                print(f"   - Birth Center: {child.get('birth_health_center')}")
                print(f"   - Detail: {child.get('place_of_birth_detail')}")
            else:
                print(f"   ❌ Missing fields: {missing}")
        else:
            print("   ⚠️ No children found to inspect. Run 'setup_test_data.py' first.")
            
    else:
        print(f"❌ Failed to fetch children. Status: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_api()
