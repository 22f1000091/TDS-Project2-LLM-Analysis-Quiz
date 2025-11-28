import asyncio
from playwright.async_api import async_playwright

async def scrape_task_page(url: str):
    """
    Visits the page, waits for JS execution, returns text and links.
    """
    async with async_playwright() as p:
        # Launch browser (headless=True is faster)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(url, timeout=30000)
            
            # Wait for the encoded content to likely appear
            # The prompt mentioned <div id="result">
            try:
                await page.wait_for_selector("body", timeout=5000)
            except:
                pass # Proceed anyway if timeout

            # Get the full text content (visible to human)
            content = await page.inner_text("body")
            
            # Extract all hrefs (for file downloads)
            links = await page.eval_on_selector_all("a", "els => els.map(e => ({text: e.innerText, href: e.href}))")
            
            return {
                "text": content,
                "links": links
            }
        except Exception as e:
            print(f"Scraping Error: {e}")
            return {"text": "", "links": []}
        finally:
            await browser.close()