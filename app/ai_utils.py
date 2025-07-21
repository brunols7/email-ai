import os
import json
import google.generativeai as genai
from typing import List, Optional
from app.models.category import Category
import re
from playwright.async_api import async_playwright
import asyncio
from uuid import uuid4
from google.api_core.exceptions import ResourceExhausted

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
    
    category_list_str += '\n- "Other": Use this category for any email that does not clearly fit into the other categories.'


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
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_response)
    except ResourceExhausted as e:
        print(f"Gemini API rate limit exceeded during summarization: {e}")
        raise e  
    except Exception as e:
        print(f"Error calling Gemini API or parsing JSON: {e}")
        return None
    
def find_unsubscribe_link(body: str) -> Optional[str]:
    prompt = f"""
Analyze the following email's HTML body. Your task is to find the most likely URL for unsubscribing from this newsletter or mailing list.

Look for anchor tags (`<a>`) with text like "unsubscribe", "manage your preferences", "opt-out", or similar phrases.

Return ONLY the URL from the `href` attribute of that anchor tag. Do not return any other text, explanation, or formatting. If no link is found, return the string "None".

HTML Body:
\"\"\"
{body}
\"\"\"

Unsubscribe URL:
"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        url_match = re.search(r'https?://[^\s"]+', response.text)
        if url_match:
            url = url_match.group(0)
            return url.strip().strip('.').strip(',')
            
        return None
    except ResourceExhausted as e:
        print(f"Gemini API rate limit exceeded during link finding: {e}")
        raise e
    except Exception as e:
        print(f"Error calling Gemini API to find unsubscribe link: {e}")
        return None

async def agent_unsubscribe_from_link(url: str) -> dict:
    if not url or "http" not in url:
        return {"success": False, "reason": "Invalid URL."}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=60000)
            
            await asyncio.sleep(3)

            html_content = await page.content()

            prompt = f"""
            Analyze the following HTML from an 'unsubscribe' page. Your task is to identify the CSS selector
            of the clickable element (either a <button>, <a>, or <input type="submit">) that confirms and completes
            the unsubscribe action. Prioritize elements with text like "Unsubscribe", "Confirm", "Save Preferences", "Submit".
            Ignore links that navigate to unrelated pages, such as "back to site".

            Respond ONLY with a JSON object in the format:
            {{"selector": "CSS_SELECTOR_HERE"}}

            If no clear confirmation selector is found, respond with:
            {{"selector": null}}

            HTML:
            \"\"\"
            {html_content[:10000]}
            \"\"\"
            """

            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
            result_json = json.loads(cleaned_response)
            
            selector = result_json.get("selector")

            if not selector:
                await browser.close()
                return {"success": False, "reason": "AI could not identify a confirmation button on the page."}

            await page.click(selector, timeout=25000)
            
            await asyncio.sleep(2)
            screenshot_path = f"unsubscribe_{uuid4()}.png"
            await page.screenshot(path=screenshot_path)

            await browser.close()
            
            return {"success": True, "reason": f"Unsubscribe action executed. Screenshot saved at {screenshot_path}"}
    except ResourceExhausted as e:
        print(f"Gemini API rate limit exceeded during unsubscribe agent: {e}")
        return {"success": False, "reason": "Gemini API rate limit was exceeded during this operation."}
    except Exception as e:
        print(f"Error in unsubscribe agent for URL {url}: {e}")
        return {"success": False, "reason": str(e)}