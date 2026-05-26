#import requests
from curl_cffi import requests
from bs4 import BeautifulSoup
import os
import io
from pypdf import PdfReader
import difflib

TARGETS = {
    "jpm_eotm": "https://privatebank.jpmorgan.com/nam/en/insights/latest-and-featured/eotm",
    "blackrock_weekly": "https://www.blackrock.com/us/individual/insights/blackrock-investment-institute/weekly-commentary",
    "tickmill_insight": "https://www.tickmill.com/blog/category/market-insight",
    "ubs_monthly": "https://www.ubs.com/global/en/wealthmanagement/insights/chief-investment-office/house-view/articles/monthly.html",
    "bofa_hartnett": "https://olui2.fs.ml.com/RIResearchReportsUI/BofAMLSearch.aspx?ResearchSearchQuery=TWljaGFlbCUyMEhhcnRuZXR0&NTR_RUN=RUN_RIResearchReportsUI_BofAMLHub",
    "ms_gic_weekly": "https://www.morganstanley.com/content/dam/mscampaign/wealth-management/wmir-assets/gic-weekly.pdf",
    "ms_gic_otm": "https://www.morganstanley.com/content/dam/mscampaign/wealth-management/wmir-assets/On-The-Markets.pdf",
    "strs_ohio": "https://www.strsoh.org/about/board-meetings.html",
}

def fetch_content(name, url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate", # No 'br' to avoid binary gibberish
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0"
    }
    
    #response = requests.get(url, headers=headers, timeout=30)
    response = requests.get(url, headers=headers, timeout=30, impersonate="chrome110")
    
    if response.status_code != 200:
        print(f"⚠️ [{name}] Failed with status code: {response.status_code}")
        return None

    # Check if the response is a PDF
    content_type = response.headers.get('Content-Type', '').lower()
    if 'application/pdf' in content_type or url.lower().endswith('.pdf'):
        print(f"📄 [{name}] Detected PDF. Extracting text...")
        # Read the PDF directly from memory
        pdf_file = io.BytesIO(response.content)
        reader = PdfReader(pdf_file)
        
        pdf_text = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                pdf_text.append(extracted)
                
        return '\n'.join(pdf_text)

    # If it's not a PDF, handle it as HTML
    print(f"🌐 [{name}] Detected HTML. Parsing webpage...")
    response.encoding = 'utf-8' 
    soup = BeautifulSoup(response.text, 'html.parser')
    
    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'meta', 'noscript', 'iframe']):
        element.decompose()
        
    lines = (line.strip() for line in soup.get_text().splitlines())
    chunks = (phrase for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    if len(text.strip()) < 200:
        print(f"⚠️ [{name}] Warning: Pulled very little text ({len(text)} chars). Page might be dynamic or blocked.")
        
    return text

def main():
    os.makedirs('data', exist_ok=True)
    
    # We set a threshold for what constitutes a "real" update.
    # 0.98 means the page must be LESS than 98% identical to trigger an update.
    # A completely new article dropping onto a page will usually drop similarity to 80-95%.
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

            # If we have old content, calculate how similar it is to the new content
            if old_content:
                similarity = difflib.SequenceMatcher(None, old_content, content).ratio()
                print(f"📊 Similarity for {name}: {similarity:.2%}")
                
                if similarity >= SIMILARITY_THRESHOLD:
                    print(f"⏭️  Skipped {name}: Changes were too minor (likely editorial).")
                    continue # Skip the file write completely
                else:
                    print(f"🚨 Significant change detected for {name}!")

            # If it passes the threshold (or if it's a brand new file), overwrite it
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ Successfully saved new data to {name}.txt")
            
        except Exception as e:
            print(f"❌ Error processing {name}: {e}")

if __name__ == "__main__":
    main()
