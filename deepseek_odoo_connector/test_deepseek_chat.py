# Please install OpenAI SDK first: `pip3 install openai`
#
# from openai import OpenAI
#
# client = OpenAI(api_key="sk-031b34475d704c96aa8d984f9b439950", base_url="https://api.deepseek.com")
#
# response = client.chat.completions.create(
#     model="deepseek-chat",
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant"},
#         {"role": "user", "content": "Hello"},
#     ],
#     stream=True
# )
# print(response)
# print(response.choices[0].message.content)



# from openai import OpenAI
#
# # for backward compatibility, you can still use `https://api.deepseek.com/v1` as `base_url`.
# client = OpenAI(api_key="sk-031b34475d704c96aa8d984f9b439950", base_url="https://api.deepseek.com")
#
# response = client.chat.completions.create(
#     model="deepseek-chat",
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant"},
#         {"role": "user", "content": "Hello"},
#   ],
#     max_tokens=1024,
#     temperature=0.7,
#     stream=False
# )
#
# print(response.choices[0].message.content)


import requests
import json

url = "https://api.deepseek.com/chat/completions"

payload = json.dumps({
  "messages": [
    {
      "content": "You are a helpful assistant",
      "role": "system"
    },
    {
      "content": "Hi",
      "role": "user"
    }
  ],
  "model": "deepseek-chat",
  "frequency_penalty": 0,
  "max_tokens": 2048,
  "presence_penalty": 0,
  "response_format": {
    "type": "text"
  },
  "stop": None,
  "stream": False,
  "stream_options": None,
  "temperature": 1,
  "top_p": 1,
  "tools": None,
  "tool_choice": "none",
  "logprobs": False,
  "top_logprobs": None
})
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'Authorization': 'Bearer sk-031b34475d704c96aa8d984f9b439950'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)