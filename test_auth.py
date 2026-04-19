import requests
import json

base_url = "http://127.0.0.1:8000/api/auth"

r_login = requests.post(f"{base_url}/login/", json={"login": "testuser", "password": "testpassword123"})
if r_login.status_code != 200:
    print("Login failed", r_login.text)
    exit(1)

token = r_login.json()['tokens']['access']
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

r_post = requests.post(f"{base_url}/faces/", headers=headers, json={"full_name": "Test Script", "role": "Студент", "allowed_cameras": []})
print("POST status:", r_post.status_code)
print("POST body:", r_post.text)
