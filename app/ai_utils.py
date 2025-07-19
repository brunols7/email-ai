import os
import json
import google.generativeai as genai
from typing import List
from app.models.category import Category

try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not set in the environment variables")
    genai.configure(api_key=api_key)
except Exception as e:
    print(f"Error configuring Google API: {e}")


def summarize_and_categorize_email(body: str, user_categories: List[Category]) -> dict:
    category_list_str = "\n".join(
        [f'- "{cat.name}": {cat.description}' for cat in user_categories]
    )
    
    category_list_str += '\n- "Outros": Use esta categoria para qualquer e-mail que não se encaixe claramente nas outras categorias.'


    prompt = f"""
Analyze the email content below. Your task is:
1. Summarize the email in a single sentence.
2. Classify the email into ONE of the user-defined categories provided. You MUST choose one from the list.

User Categories:
{category_list_str}

Email Content:
\"\"\"
{body[:8000]}
\"\"\"

Respond ONLY with a valid JSON object in the following format, with no other text or formatting:
{{"summary": "Your one-sentence summary here", "category": "The Exact Name of the Chosen Category"}}
"""

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Generate the content
        response = model.generate_content(prompt)
        
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        
        # Parse the JSON
        return json.loads(cleaned_response)

    except Exception as e:
        print(f"Error calling Gemini API or parsing JSON: {e}")
        return None