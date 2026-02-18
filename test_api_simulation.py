import os
import django
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from medical.models import Family, Child, HealthCenter

User = get_user_model()

def print_response(response, description):
    print(f"\n--- {description} ---")
    print(f"Status Code: {response.status_code}")
    try:
        print("JSON Response:")
        print(json.dumps(response.json(), indent=4, ensure_ascii=False))
    except:
        print("Raw Response:", response.content.decode())

def run_simulation():
    print("🚀 Starting Postman Simulation (Testing API Endpoints)...")
    
    # 1. Setup Test Data
    print("\n🛠️  Setting up test user and data...")
    # Create User
    user, created = User.objects.get_or_create(username='test_api_user', defaults={'email': 'test@api.com', 'role': 'CUSTOMER'})
    user.set_password('testpass123')
    user.save()
    
    # Create Token (simulate login or ensure user has token)
    token, _ = Token.objects.get_or_create(user=user)

    # Create Family Profile
    family, _ = Family.objects.get_or_create(
        account=user,
        defaults={
            'father_name': 'أحمد محمد', 
            'mother_name': 'فاطمة علي',
            'access_code': '123456'
        }
    )

    # Create Child
    child, _ = Child.objects.get_or_create(
        family=family,
        full_name='خالد أحمد',
        defaults={
            'gender': 'M',
            'date_of_birth': '2025-01-01'
        }
    )

    client = APIClient()

    # 2. Test Login Endpoint
    print("\n📡 [POST] /api/login/")
    login_response = client.post('/api/login/', {'username': 'test_api_user', 'password': 'testpass123'}, format='json')
    print_response(login_response, "Login Response")

    if login_response.status_code == 200:
        auth_token = login_response.json().get('token')
        
        # 3. Test Family Profile Endpoint (Authentication Required)
        print(f"\n📡 [GET] /api/family/ (With Token: {auth_token[:5]}...)")
        client.credentials(HTTP_AUTHORIZATION='Token ' + auth_token)
        family_response = client.get('/api/family/')
        print_response(family_response, "Family Data Response")

        # 4. Test Child Detail Endpoint
        print(f"\n📡 [GET] /api/children/{child.id}/")
        child_response = client.get(f'/api/children/{child.id}/')
        print_response(child_response, "Child Detail Response")

    else:
        print("❌ Login failed, skipping authenticated requests.")

    print("\n✅ Simulation Complete.")

if __name__ == '__main__':
    run_simulation()
