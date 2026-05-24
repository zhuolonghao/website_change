import requests
from bs4 import BeautifulSoup
import os

# Add your target URLs here
TARGETS = {
    "jpm_eotm": "https://privatebank.jpmorgan.com/nam/en/insights/latest-and-featured/eotm"
}

def fetch_content(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Strip out dynamic or noisy DOM elements to prevent false-positive diffs
    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'meta', 'noscript']):
        element.decompose()
        
    # Optional: If you inspect the JPM page, you could also target just the main article container
    # main_content = soup.find('main') 
    # if main_content: soup = main_content

    # Extract raw text and collapse whitespace
    text = '\n'.join([line for line in soup.stripped_strings])
    return text

def main():
    os.makedirs('data', exist_ok=True)
    
    for name, url in TARGETS.items():
        try:
            print(f"Fetching {name}...")
            content = fetch_content(url)
            
            with open(f"data/{name}.txt", "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Successfully updated {name}.txt")
            
        except Exception as e:
            print(f"Error scraping {name}: {e}")

if __name__ == "__main__":
    main()