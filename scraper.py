import os
import io
import difflib
from bs4 import BeautifulSoup
from pypdf import PdfReader
from curl_cffi import requests
from playwright.sync_api import sync_playwright

TARGETS = {
    "jpm_eotm": "https://privatebank.jpmorgan.com/nam/en/insights/latest-and-featured/eotm",
    "blackrock_weekly": "https://www.blackrock.com/us/individual/insights/blackrock-investment-institute/weekly-commentary",
    "tickmill_insight": "https://www.tickmill.com/blog/category/market-insight",
    "ubs_monthly": "https://www.ubs.com/global/en/wealthmanagement/insights/chief-investment-office/house-view/articles/monthly.html",
    "bofa_hartnett": "https://olui2.fs.ml.com/RIResearchReportsUI/BofAMLSearch.aspx?ResearchSearchQuery=TWljaGFlbCUyMEhhcnRuZXR0&NTR_RUN=RUN_RIResearchReportsUI_BofAMLHub",
    "ms_gic_weekly": "https://www.morganstanley.com/content/dam/mscampaign/wealth-management/wmir-assets/gic-weekly.pdf",
    "ms_gic_otm": "https://www.morganstanley.com/content/dam/mscampaign/wealth-management/wmir-assets/On-The-Markets.pdf",
    # Add your other targets back here
}

def fetch_with_playwright(url):
    """Fallback method that opens a real headless browser to solve JS challenges."""
    print(f"   🤖 Launching headless browser to bypass firewall...")
    with sync_playwright() as p:
        # Launch Chromium invisibly
        browser = p.chromium.launch(headless=True)
        # Create a context that perfectly mimics a real user
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        
        try:
            # Go to the URL and wait until the network is quiet (JS is done loading)
            page.goto(url, wait_until="networkidle", timeout=45000)
            
            # Give the firewall an extra 5 seconds to process its math puzzle
            page.wait_for_timeout(5000)
            
            # Extract the fully rendered HTML
            html = page.content()
            return html
        except Exception as e:
            print(f"   ❌ Browser automation failed: {e}")
            return None
        finally:
            browser.close()

def fetch_content(name, url):
    # Try the fast curl_cffi way first. 
    # Notice we drop the manual headers so it doesn't break the impersonation fingerprint.
    response = requests.get(url, timeout=30, impersonate="chrome120")
    
    html_text = ""
    
    if response.status_code in [401, 403]:
        print(f"⚠️ [{name}] 403 Blocked. Deploying browser fallback...")
        # If blocked, use Playwright to get the HTML
        html_text = fetch_with_playwright(url)
        if not html_text:
            return None
    elif response.status_code != 200:
        print(f"⚠️ [{name}] Failed with status code: {response.status_code}")
        return None
    else:
        # Check if it's a PDF (only do this for the fast requests)
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/pdf' in content_type or url.lower().endswith('.pdf'):
            print(f"📄 [{name}] Detected PDF. Extracting text...")
            pdf_file = io.BytesIO(response.content)
            reader = PdfReader(pdf_file)
            
            pdf_text = []
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    pdf_text.append(extracted)
                    
            return '\n'.join(pdf_text)
            
        # It was a successful 200 HTML page from curl_cffi
        html_text = response.text

    # Parse the resulting HTML (whether from curl_cffi or Playwright)
    print(f"🌐 [{name}] Parsing webpage...")
    soup = BeautifulSoup(html_text, 'html.parser')
    
    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'meta', 'noscript', 'iframe']):
        element.decompose()
        
    lines = (line.strip() for line in soup.get_text().splitlines())
    chunks = (phrase for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    if len(text.strip()) < 200:
        print(f"⚠️ [{name}] Warning: Pulled very little text ({len(text)} chars). Page might be heavily dynamic or permanently blocked.")
        
    return text

def main():
    os.makedirs('data', exist_ok=True)
    
    # 0.98 means the page must be LESS than 98% identical to trigger an update.
    SIMILARITY_THRESHOLD = 0.98 
    
    for name, url in TARGETS.items():
        print(f"Fetching {name}...")
        try:
            content = fetch_content(name, url)
            
            if not content:
                print(f"❌ Skipped updating {name}.txt due to fetch errors.")
                continue

            filepath = f"data/{name}.txt"
            old_content = ""
            
            # Read the existing file to compare against
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    old_content = f.read()

            # If we have old content, calculate similarity
            if old_content:
                similarity = difflib.SequenceMatcher(None, old_content, content).ratio()
                print(f"📊 Similarity for {name}: {similarity:.2%}")
                
                if similarity >= SIMILARITY_THRESHOLD:
                    print(f"⏭️  Skipped {name}: Changes were too minor (likely editorial).")
                    continue 
                else:
                    print(f"🚨 Significant change detected for {name}!")

            # Overwrite or create new file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ Successfully saved new data to {name}.txt")
            
        except Exception as e:
            print(f"❌ Error processing {name}: {e}")

if __name__ == "__main__":
    main()
