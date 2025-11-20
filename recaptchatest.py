import asyncio
import os
import warnings
import random
import json
import time
from faker import Faker
from dotenv import load_dotenv
from browser_use.agent.service import Agent
from browser_use import Controller
from browser_use.llm import ChatGoogle    # ✅ use browser_use's Gemini wrapper (not LangChain)
from pydantic import BaseModel
from playwright.async_api import BrowserContext, async_playwright
import requests
from fake_useragent import UserAgent
from langchain.tools import tool, Tool

warnings.simplefilter("ignore", ResourceWarning)

fake = Faker()

class Formsubmissionresult(BaseModel):
    url_entry_status: str
    cookie_banner_close_status: str
    Talk_to_us_click_status: str
    form_modal_open_status: str
    form_fill_and_submit_status: str
    thank_you_screen_confirmation_message_status: str

controller = Controller(output_model=Formsubmissionresult)

load_dotenv()

def generate_random_test_data():
    return {
        "first_name": fake.first_name(),
        "last_name": "TESTTEST",   # Always fixed as per requirement from BR
        "email": fake.unique.email(),
        "phone": fake.msisdn(),    # ensures a digit-based valid phone
        "company": fake.company(),
        "country": "United States",
        "comment": fake.text(max_nb_chars=150)
    }

def get_random_user_agent():
    ua = UserAgent()
    return ua.random

def get_random_proxy():
    return None

async def SiteValidation():
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY or GEMINI_API_KEY not found in environment variables")

    test_data = generate_random_test_data()

    task = (
        f"Role: You are a Human-Like UI Automation Tester.\n"
        "Your task is to fill out and submit the form(s) on the webpage accurately.\n"
        "Important Instructions:\n"
        "- Absolutely avoid using any numeric indexes (like index: 15). These are unstable and lead to errors.\n"
        "- Always identify elements by their:\n"
        "  - Visible label (e.g., 'First Name')\n"
        "  - Placeholder attribute (e.g., placeholder=\"Enter your name\")\n"
        "  - Name or aria-label (e.g., name=\"email\", aria-label=\"Phone Number\")\n"
        "- Use XPath or CSS selectors only when tied to semantic attributes, not DOM order.\n"
        "- For dropdowns, open the dropdown and select options by their visible text.\n"
        "  If that fails, fall back to simulating key presses to select 'United States'.\n"
        "- Before typing, wait until the element is visible and interactive.\n"
        "- After typing, verify the input value using DOM read-back.\n"
        "- Detect reCAPTCHA by checking for an iframe with 'recaptcha' in the src.\n"
        "- Do NOT attempt to solve or click the CAPTCHA checkbox programmatically to avoid bot detection.\n"
        "- Perform human-like typing with varied delays and realistic mouse movement.\n"
        "- Do not reset progress after an interruption. Resume from last completed step.\n"
        "Steps to Perform:\n"
        #"1. Navigate to the webpage using Basic Authentication: https://broadridgedigital:broadridge1@www-dev.broadridge.com/resource/webinar/capital-markets/panel-discussion-the-future-of-post-trade-operations\n"
        "1. Navigate to the webpage : https://www.broadridge.com/\n"
        "2. Wait for the full page to load completely.\n"
        "3. Close the cookie banner at the bottom by clicking the \"Close\" button. Wait for the banner to be dismissed.\n"
        "4. Detect all unique forms present on the page.\n"
        "4a. If the page contains multiple forms (e.g., an inline form on the page and another one accessible via the \"Contact Us\" call-to-action), identify them separately by their unique visible labels, placeholders, or form headings.\n"
        "4b. For each detected form:\n"
        "    - If it is an inline form, interact directly with it.\n"
        "    - If it requires a CTA (e.g., clicking the \"Contact Us\" button), open it once and only once.\n"
        "    - Verify that all fields are visible, properly labeled, and interactive.\n"
        "    - Fill and submit it once using a fresh, randomized, valid dataset.\n"
        "    - After submission, wait for and verify the confirmation or 'Thank You' message before continuing.\n"
        "    - Once a form is successfully submitted, mark it as completed by recording its unique identifier (heading, form label, or first field placeholder). Do not re-open, re-trigger, or re-submit this form again during the session.\n"
        "4c. If a form is not present or cannot be located (on-page or via the CTA), skip it gracefully. Do NOT loop endlessly or attempt to hallucinate missing elements.\n"
        "4d. Ensure that each located form uses a newly randomized dataset for every submission. All values (First Name, Email, Phone, Comment) must be unique and randomized per run, except the Last Name which must always remain 'TESTTEST'.\n"
        f"5. For each form submission, fill all mandatory fields with fresh, randomized, and valid data:\n"
        f"   - First Name: {test_data['first_name']}\n"
        f"   - Last Name: TESTTEST \n"
        f"   - Email: {test_data['email']}\n"
        f"   - Phone Number: {test_data['phone']}\n"
        "   - Country: Open the dropdown and try selecting 'United States' by visible text.\n"
        "     If not successful, use keyboard navigation (ArrowDown + Enter) to select.\n"
        f"   - Comment: {test_data['comment']}\n"
        "   After filling, verify DOM values match the entered values before submitting.\n"
        "6. Detect reCAPTCHA by checking for an iframe with 'recaptcha' in the src.\n"
        "6a. If reCAPTCHA is detected on a staging or test environment, skip interacting with the checkbox because test keys will auto-validate.\n"
        "6b. Assume the reCAPTCHA passes automatically and proceed to the form submission step.\n"
        "7. Do NOT attempt to solve or click the reCAPTCHA checkbox programmatically on production.\n"
        "   -On staging with test keys, treat reCAPTCHA as bypassed.\n"
        "8. Submit the currently active form using its visible submit button. Do NOT re-click the \"Contact Us\" CTA or re-submit any form that has already been successfully submitted and marked as completed.\n"
        "9. After submission, wait for the \"Thank You\" message to appear.\n"
        "10. Capture a screenshot of the confirmation page.\n"
        "11. Close the browser session.\n"
        "Execution Rules:\n"
        "- Wait until elements are visible and interactive before acting.\n"
        "- Skip any optional or hidden fields that might block submission.\n"
        "- If a form cannot be found, skip it gracefully and proceed with remaining steps.\n"
        "- Do not reuse data across runs or across multiple forms on the same page.\n"
        "- Never resubmit a form or re-trigger a CTA/modal after one successful submission.\n"
        "- Maintain a log of completed forms (by form heading, unique label, or first field placeholder) and skip them if encountered again in the same session.\n"
        "- Follow all steps in order.\n"
    )

    try:
        llm = ChatGoogle(model="gemini-2.0-flash", api_key=api_key)
    except Exception as e:
        print("Model not available, falling back to 'gemini-1.5-flash'", e)
        llm = ChatGoogle(model="gemini-2.5-flash-lite", api_key=api_key)

    agent = Agent(
        task=task,
        llm=llm,
        controller=controller,
        use_vision=True
    )

    print("Starting agent task...")
    history = await agent.run()
    test_result = history.final_result()

    print("Test result:")
    if isinstance(test_result, str):
        test_result = json.loads(test_result)
        print(json.dumps(test_result, indent=2))

    with open("submission_result.json", "w") as f:
        json.dump(test_result, f, indent=2)


if __name__ == "__main__":
    asyncio.run(SiteValidation())
