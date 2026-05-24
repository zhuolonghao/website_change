import requests
from bs4 import BeautifulSoup
import os

TARGETS = {
    "jpm_eotm": "https://privatebank.jpmorgan.com/nam/en/insights/latest-and-featured/eotm",
    "blackrock_weekly": "https://www.blackrock.com/us/individual/insights/blackrock-investment-institute/weekly-commentary",
    "ms_gio": "https://digitalcontent.morganstanleyclientserv.com/lp/global-investment-office-insights.html",
    "tickmill_insight": "https://www.tickmill.com/blog/category/market-insight",
    "ubs_monthly": "https://www.ubs.com/global/en/wealthmanagement/insights/chief-investment-office/house-view/articles/monthly.html",
    "bofa_hartnett": "https://olui2.fs.ml.com/RIResearchReportsUI/BofAMLSearch.aspx?ResearchSearchQuery=TWljaGFlbCUyMEhhcnRuZXR0&NTR_RUN=RUN_RIResearchReportsUI_BofAMLHub"
}

def fetch_content(name, url):
    # Expanded headers to better mimic a premium desktop browser session
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0"
    }
    
    response = requests.get(url, headers=headers, timeout=20)
    
    # Handle response errors gracefully without crashing the whole loop
    if response.status_code != 200:
        print(f"⚠️ [{name}] Failed with status code: {response.status_code}")
        return None
        
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Strip layout noise
    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'meta', 'noscript', 'iframe']):
        element.decompose()
        
    # Get stripped lines and discard completely blank rows
    lines = (line.strip() for line in soup.get_text().splitlines())
    chunks = (phrase for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    # If the page is completely empty or just returns a basic placeholder
    if len(text.strip()) < 200:
        print(f"⚠️ [{name}] Warning: Pulled very little text ({len(text)} chars). Page might be dynamic or blocked.")
        
    return text

def main():
    os.makedirs('data', exist_ok=True)
    
    for name, url in TARGETS.items():
        print(f"Fetching {name}...")
        content = fetch_content(name, url)
        
        if content:
            with open(f"data/{name}.txt", "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ Successfully updated {name}.txt")
        else:
            print(f"❌ Skipped updating {name}.txt due to errors.")

if __name__ == "__main__":
    main()
