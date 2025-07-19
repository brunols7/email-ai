import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

def summarize_and_categorize_email(body: str) -> dict:
    prompt = f"""
You are an intelligent assistant. Analyze the email content below, summarize it in 2 sentences max, and classify it into one of the following categories:
[Work, Promotions, Social, Updates, Personal, Other]

Email:
\"\"\"
{body}
\"\"\"

Respond in this format (JSON only):
{{"summary": "...", "category": "..."}}
"""

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=150
    )

    content = response.choices[0].message.content
    return eval(content) 