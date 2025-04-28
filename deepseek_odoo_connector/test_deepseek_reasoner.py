from openai import OpenAI
client = OpenAI(api_key="sk-031b34475d704c96aa8d984f9b439950", base_url="https://api.deepseek.com")

# Round 1
messages = [{"role": "user", "content": "9.11 and 9.8, which is greater?"}]
response = client.chat.completions.create(
    model="deepseek-reasoner",
    messages=messages
)

reasoning_content = response.choices[0].message.reasoning_content
content = response.choices[0].message.content

# # Round 2
# messages.append({'role': 'assistant', 'content': content})
# messages.append({'role': 'user', 'content': "How many Rs are there in the word 'strawberry'?"})
# response = client.chat.completions.create(
#     model="deepseek-reasoner",
#     messages=messages
# )
# # ...