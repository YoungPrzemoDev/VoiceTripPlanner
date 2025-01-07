from openai import OpenAI
import os

client = OpenAI()
MODEL = "gpt-4o-mini"
client.api_key = os.getenv("OPEN_AI_API_KEY")


completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": "Write a haiku about recursion in programming."
        }
    ]
)

print(completion.choices[0].message)