import asyncio
from playwright.async_api import async_playwright

async def run():
    mathjax_config = "<script>MathJax = {tex: {inlineMath: [['$','$'], ['\\\\(','\\\\)']], displayMath: [['$$','$$'], ['\\\\[','\\\\]']]}};</script>"
    mathjax_script = f'{mathjax_config}<script id="MathJax-script" src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>'
    html = f"<!DOCTYPE html><html><head><meta charset='UTF-8'>{mathjax_script}</head><body>$$ x^2 + y^2 = z^2 $$<p>Done.</p></body></html>"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            print("1. Setting content")
            await page.set_content(html, wait_until="networkidle", timeout=15000)
            print("2. Content set, evaluating MathJax")
            # See what window.MathJax is
            is_mathjax = await page.evaluate("!!window.MathJax")
            print(f"MathJax exists: {is_mathjax}")
            if is_mathjax:
                has_promise = await page.evaluate("!!window.MathJax.typesetPromise")
                print(f"typesetPromise exists: {has_promise}")
                # Wait for MathJax to finish
                print("3. Waiting for MathJax styles or typeset...")
                # await page.wait_for_function("window.MathJax && window.MathJax.typesetPromise", timeout=5000)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

asyncio.run(run())
