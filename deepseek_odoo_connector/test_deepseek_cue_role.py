from openai import OpenAI

client = OpenAI(
    base_url="https://api.deepseek.com/",
    api_key="sk-031b34475d704c96aa8d984f9b439950"
)

completion = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {
                "role": "user",
                "content": "假设诸葛亮死后在地府遇到了刘备，请模拟两个人展开一段对话。"
        }
    ]
)

print(completion.choices[0].message.content)