import asyncio
import os
import json
import warnings
from faker import Faker
from dotenv import load_dotenv

# Playwright for deterministic pre-click
try:
    from playwright.async_api import async_playwright
except Exception:
    async_playwright = None

from browser_use.agent.service import Agent
from browser_use import Controller
from browser_use.llm import ChatGoogle
from pydantic import BaseModel

warnings.simplefilter("ignore", ResourceWarning)
fake = Faker()
load_dotenv()

# ----------- RESULT MODEL -----------
class Formsubmissionresult(BaseModel):
    url_entry_status: str
    cookie_banner_close_status: str
    promo_popup_close_status: str
    Schedule_a_demo_click_status: str
    form_modal_open_status: str
    form_fill_and_submit_status: str
    thank_you_screen_confirmation_message_status: str

controller = Controller(output_model=Formsubmissionresult)

# ----------- DATA GENERATION -----------
def generate_random_test_data():
    return {
        "first_name": fake.first_name(),
        "last_name": "TESTTEST",
        "email": fake.unique.email(),
        "phone": fake.msisdn()[:10],
        "company": fake.company(),
        "job_title": fake.job(),
        "country": "United States",
        "comment": fake.text(max_nb_chars=150),
    }

# ----------- Playwright helper to close overlays (ONLY FIXED PART) -----------
async def close_promotional_popup(page):
    js_script = """
    (() => {
        try {
            // click close button if present
            const closeBtn = document.querySelector('.popup-content.active .close');
            if (closeBtn) {
                closeBtn.click();
                return 'close-button-clicked';
            }

            // remove popup wrapper if still present
            const popup = document.querySelector('.popup-content.active');
            if (popup) {
                popup.remove();
                return 'popup-removed';
            }

            return 'no-popup-found';
        } catch(e) {
            return 'error:' + e.toString();
        }
    })();
    """
    try:
        result = await page.evaluate(js_script)
        print("🟦 Promo popup close result:", result)
    except Exception as e:
        print(f"⚠️ Could not evaluate JS to close promo popup: {e}")

# ----------- Playwright pre-step: deterministic CTA click -----------
async def ensure_schedule_demo_modal(playwright_timeout=10000, screenshot_path="modal_confirmation.png"):
    if async_playwright is None:
        print("⚠️ Playwright is not installed. Install it with:\n  pip install playwright\n  playwright install chromium\nThen re-run this script.")
        raise SystemExit(1)

    url = "https://www.broadridge.com/advisor/greeting-cards"
    print("🧭 (Pre-step) Opening page with Playwright to click CTA reliably...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(1.0)

        # Close cookie banner if present
        try:
            await page.wait_for_selector("#onetrust-accept-btn-handler", timeout=3000)
            await page.click("#onetrust-accept-btn-handler")
            print("✅ Cookie banner closed (Playwright).")
            await asyncio.sleep(0.5)
        except Exception:
            print("ℹ️ Cookie banner not found or already closed (Playwright).")

        # Close promotional popup (FIXED)
        await close_promotional_popup(page)

        # Robust JS click
        robust_click_js = r"""
        (function(selector){
          function findDeep(selector, root=document){
            const el = root.querySelector(selector);
            if (el) return el;
            const walker = document.createTreeWalker(document, NodeFilter.SHOW_ELEMENT, null, false);
            while(walker.nextNode()){
              const node = walker.currentNode;
              if (node.shadowRoot){
                try{
                  const found = node.shadowRoot.querySelector(selector);
                  if (found) return found;
                }catch(e){}
              }
            }
            return null;
          }
          const el = findDeep(selector);
          if(!el) return {ok:false, reason:'not-found'};
          try{ el.scrollIntoView({behavior:'auto', block:'center', inline:'center'}); }catch(e){}
          try{ if(typeof el.click === 'function'){ el.click(); return {ok:true, method:'native'}; } }catch(e){}
          try{
            const rect = el.getBoundingClientRect();
            const x = rect.left + rect.width/2;
            const y = rect.top + rect.height/2;
            ['mouseover','mousemove','mousedown','mouseup','click'].forEach(function(name){
              el.dispatchEvent(new MouseEvent(name, {view:window,bubbles:true,cancelable:true,clientX:x,clientY:y,composed:true})));
            });
            return {ok:true, method:'simulated'};
          }catch(e){
            return {ok:false, reason:String(e)};
          }
        })("a#header-talk-to-us-link.js-open-modal");
        """

        clicked = False
        attempt = 0
        click_result = None
        while attempt < 3 and not clicked:
            attempt += 1
            try:
                click_result = await page.evaluate(robust_click_js)
                if isinstance(click_result, dict) and click_result.get("ok"):
                    clicked = True
                    print(f"✅ CTA click succeeded (attempt {attempt}) - method: {click_result.get('method')}")
                    break
                else:
                    print(f"ℹ️ CTA click attempt {attempt} returned: {click_result}")
            except Exception as e:
                print(f"⚠️ Playwright evaluate error on attempt {attempt}: {e}")
            await asyncio.sleep(1.0)

        if not clicked:
            try:
                found = await page.query_selector("a#header-talk-to-us-link.js-open-modal")
                if found:
                    await found.scroll_into_view_if_needed()
                    await found.click()
                    clicked = True
                    print("✅ CTA clicked via simple selector fallback.")
                else:
                    print("❌ CTA element not found in DOM after retries.")
            except Exception as e:
                print(f"⚠️ Final fallback click failed: {e}")

        try:
            await page.wait_for_selector("form.form--validate.blueState-form", timeout=playwright_timeout)
            print("✅ Modal form detected (Playwright).")
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 Screenshot saved to {screenshot_path}")
            modal_ok = True
        except Exception:
            print("❌ Modal did not appear within timeout (Playwright).")
            modal_ok = False

        await browser.close()
        return {"cta_clicked": clicked, "click_result": click_result, "modal_ok": modal_ok, "screenshot": screenshot_path}

# ----------- MAIN AUTOMATION LOGIC -----------
async def SiteValidation():
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("Missing GOOGLE_API_KEY or GEMINI_API_KEY in .env")

    test_data = generate_random_test_data()

    pre = await ensure_schedule_demo_modal()
    print("Pre-step result:", pre)

    # ---------------- REAL TASK (ONLY ONCE) ----------------
    task = (
        "Target URL: https://www.broadridge.com/advisor/greeting-cards\n"
        "Role: You are a precise, human-like UI automation tester.\n"
        "You must navigate to the Broadridge Advisor page, click the 'Schedule a Demo' header button, "
        "wait for the modal form to appear, and then fill and submit it accurately.\n\n"

        "Steps to follow carefully:\n"
        "1️⃣ Navigate to: https://www.broadridge.com/advisor/greeting-cards\n"
        "2️⃣ Wait for the page to fully load.\n"
        "3️⃣ Close any cookie banners (id='onetrust-accept-btn-handler' or aria-label='Close').\n"
        "3️⃣a Close promotional popup if present.\n"
        "4️⃣ Click the header button with selector a#header-talk-to-us-link.js-open-modal.\n"
        "5️⃣ Wait for form.\n"
        f"6️⃣ Fill fields:\n"
        f"    - First Name → {test_data['first_name']}\n"
        f"    - Last Name → TESTTEST\n"
        f"    - Work Email → {test_data['email']}\n"
        f"    - Telephone → {test_data['phone']}\n"
        f"    - Country → United States\n"
        f"    - Company → {test_data['company']}\n"
        f"    - Job Title → {test_data['job_title']}\n"
        "    - Preferred contact: Email\n"
        "    - Interest: product_dm\n"
        f"    - Comment → {test_data['comment']}\n"
        "7️⃣ Detect recaptcha iframe (skip).\n"
        "8️⃣ Click submit.\n"
        "9️⃣ Wait for thank-you screen.\n"
    )

    # ---------------- Load LLM ----------------
    try:
        llm = ChatGoogle(model="gemini-2.5-flash-lite", api_key=api_key)
    except Exception:
        llm = ChatGoogle(model="gemini-1.5-flash", api_key=api_key)

    # ---------------- Create Agent (ONLY ONCE) ----------------
    agent = Agent(task=task, llm=llm, controller=controller, use_vision=True)
    print("🚀 Agent initialized. Applying CTA fix inside browser-use...")

    # ---------------- CTA FIX (CORRECT LOCATION) ----------------
    try:
        result = await controller.evaluate(code="""
            (function(){
                const el = document.querySelector('#header-talk-to-us-link');
                if (!el) return 'CTA not found';
                try { el.click(); return 'CTA clicked'; }
                catch(e){ return 'CTA click error: ' + e.toString(); }
            })();
        """)
        print("✅ CTA click returned:", result)
    except Exception as e:
        print("⚠️ CTA fix failed:", e)

    await asyncio.sleep(1)

    # ---------------- Agent Run With Retry ----------------
    async def run_with_retry(agent, retries=3, delay=10):
        for attempt in range(1, retries + 1):
            try:
                return await agent.run()
            except Exception as e:
                print(f"⚠️ Attempt {attempt}/{retries} failed ({e}). Retrying...")
                await asyncio.sleep(delay)
        raise RuntimeError("Agent failed after multiple retries.")

    # Run
    history = await run_with_retry(agent)
    result = history.final_result()

    if isinstance(result, str):
        result = json.loads(result)

    print(json.dumps(result, indent=2))

    with open("advisor_submission_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


# ----------- ENTRY POINT -----------
if __name__ == "__main__":
    asyncio.run(SiteValidation())
