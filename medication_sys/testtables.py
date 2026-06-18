import requests
import config

url = f"https://api.airtable.com/v0/meta/bases/{config.BASE_ID}/tables"
headers = {"Authorization": f"Bearer {config.AIRTABLE_TOKEN}"}

response = requests.get(url, headers=headers)
if response.status_code == 200:
    data = response.json()
    print("--- Found these tables in your Airtable Base: ---")
    for table in data['tables']:
        print(f"Name: '{table['name']}' | ID: {table['id']}")
else:
    print(f"Failed to fetch. Status code: {response.status_code}")
    print(response.text)