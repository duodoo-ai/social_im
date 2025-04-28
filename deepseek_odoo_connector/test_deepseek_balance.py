import requests

url = "https://api.deepseek.com/user/balance"

payload={}
headers = {
  'Accept': 'application/json',
  'Authorization': 'Bearer sk-031b34475d704c96aa8d984f9b439950'
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.text)