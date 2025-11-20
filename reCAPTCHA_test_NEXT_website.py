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
from browser_use.llm import ChatGoogle    # using browser_use's Gemini wrapper
from pydantic import BaseModel

warnings.simplefilter("ignore", ResourceWarning)
fake = Faker()

class Formsubmissionresult(BaseModel):
    url_entry_status: str = ""
    cookie_banner_close_status: str = ""
    promo_popup_close_or_open_status: str = ""
    form_open_status: str = ""
    form_fill_and_submit_status: str = ""
    thank_you_screen_confirmation_message_status: str = ""

controller = Controller(output_model=Formsubmissionresult)
load_dotenv()

def generate_random_test_data():
    return {
        "first_name": fake.first_name(),
        "last_name": "TESTTEST",   # per your requirement
        "email": fake.unique.email(),
        "company": fake.company(),
        "job_title": fake.job(),
    }

async def SiteValidation_next():
    """
    Automation task for https://www.broadridge.com/next/
    - Close cookie banner (multiple fallback selectors attempted)
    - Close or interact with promo popup (based on the HTML you supplied)
    - Scroll to / open the subscription anchor (#subForm)
    - Fill the form fields (id selectors taken from the provided markup)
    - Submit and verify Thank You message
    """
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY or GEMINI_API_KEY not found in environment variables")

    test_data = generate_random_test_data()

    # Task/instructions for the agent — explicit, deterministic, with fallbacks
    task = (
        "Role: You are a Human-Like UI Automation Tester.\n"
        "Target page: https://www.broadridge.com/next/\n"
        #"Target page: https://broadridgedigital:broadridge1@www-dev.broadridge.com/next/\n"
        "Goal: Close cookie banner and any promo popup, open/scroll to the subscription form (anchor #subForm), "
        "fill mandatory fields and submit once, then confirm the 'Thank you' state.\n\n"

        "Important operational rules (use semantic selectors, avoid numeric indexes):\n"
        " - Try a sequence of stable selectors for cookie/banner close:\n"
        "   1) button[aria-label='close'], button[aria-label='Close'], button.cookie-close, .cookie-banner .close,\n"
        "   2) .cookie-banner button, #cookie-close, .cookie-close\n"
        " - Attempt to dismiss the promo popup described by this outer HTML block:\n"
        "   <div class='popup-inner'> ... <a href='#subForm' class='cta'>Subscribe now!</a> ...</div>\n"
        "   - Preferred approach: if there's a visible close button (e.g., .popup-close, .popup__close, button.close), click it.\n"
        "   - If no close button, clicking the inner CTA link '.popup-inner a.cta' is acceptable (it navigates to the form anchor #subForm).\n"
        " - After closing/dismissing popups, ensure the form container with id 'subForm' is visible.\n\n"

        "Form fill instructions (use these exact form field names/ids when visible):\n"
        f" - First Name: input#name_first  -> value: {test_data['first_name']}\n"
        " - Last Name: input#lastname or input[name='name_last' ] -> value: TESTTEST\n"
        f" - Company: input#company or input[name='Company'] -> value: {test_data['company']}\n"
        f" - Job Title: input#title or input[name='job_title'] -> value: {test_data['job_title']}\n"
        f" - Work Email: input#email or input[name='email_work'] -> value: {test_data['email']}\n\n"

        "Execution details:\n"
        " - Wait until each element is visible and enabled before interacting.\n"
        " - After typing into an input, read its DOM value to verify match.\n"
        " - Submit using the visible button with type='submit' (e.g., button#sales-rep__submit_bs or .form__submit).\n"
        " - After submit, wait for the success block: .form-cta__success or a heading that contains 'Thank you'.\n"
        " - Capture and return a JSON object describing success/failure of each step.\n\n"

        "Failover and safety:\n"
        " - If reCAPTCHA iframes are present (src contains 'recaptcha'), do not attempt to solve.\n"
        " - If reCAPTCHA blocks submission on production, record that and exit gracefully.\n"
        " - Do not retry/duplicate a successful submission in the same session.\n"
    )

    # instantiate the LLM wrapper
    try:
        llm = ChatGoogle(model="gemini-2.0-flash", api_key=api_key)
    except Exception as e:
        print("Model not available, falling back to alternate model:", e)
        llm = ChatGoogle(model="gemini-2.5-flash-lite", api_key=api_key)

    agent = Agent(
        task=task,
        llm=llm,
        controller=controller,
        use_vision=True
    )

    print("Starting /next agent task...")
    history = await agent.run()
    test_result = history.final_result()

    print("Test result for /next:")
    # The agent may return either JSON string or a dict-like object depending on your agent setup
    if isinstance(test_result, str):
        try:
            test_result = json.loads(test_result)
        except Exception:
            # if agent returned a non-JSON string, wrap it
            test_result = {"raw_agent_output": test_result}

    # ensure keys exist to conform to Formsubmissionresult
    normalized = {
        "url_entry_status": test_result.get("url_entry_status", "unknown"),
        "cookie_banner_close_status": test_result.get("cookie_banner_close_status", "unknown"),
        "promo_popup_close_or_open_status": test_result.get("promo_popup_close_or_open_status", "unknown"),
        "form_open_status": test_result.get("form_open_status", "unknown"),
        "form_fill_and_submit_status": test_result.get("form_fill_and_submit_status", "unknown"),
        "thank_you_screen_confirmation_message_status": test_result.get("thank_you_screen_confirmation_message_status", "unknown"),
    }

    # write a JSON file for debugging / CI visibility
    with open("submission_result_next.json", "w") as f:
        json.dump(normalized, f, indent=2)

    print(json.dumps(normalized, indent=2))
    return normalized

if __name__ == "__main__":
    asyncio.run(SiteValidation_next())
