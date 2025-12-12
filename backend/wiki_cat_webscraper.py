import requests
from bs4 import BeautifulSoup
import csv
import re
from datetime import datetime
import os

# --- CONFIGURATION ---
# Using the simplified 'action=render' URL for a text-friendly output
SCRAPE_URL = "https://en.wikipedia.org/w/index.php?title=Cat&action=render"
CSV_FILENAME = "wikipedia_cat_data.csv"

# Essential header to simulate a real browser request
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def scrape_wikipedia_cat_to_csv(url, filename, headers):
    """
    Scrapes the Wikipedia article using a brute-force method to extract all 
    text from the body, bypassing specific <p> tags that were causing failures.
    """
    print(f"--- Starting Wikipedia scrape for: {url} ---")
    documents_to_write = [] 

    try:
        # 1. Fetch the content
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() 

        soup = BeautifulSoup(response.content, 'html.parser')

        # 2. BRUTE-FORCE: Forget specific classes and IDs. Get the entire body.
        main_content_container = soup.find('body')
        
        # If the body tag is somehow missing (highly unlikely), use the entire document
        if not main_content_container:
            main_content_container = soup
        
        # 3. EXTRACT AND CLEAN ALL TEXT NODES (Ignoring <p> tags entirely)
        # Use get_text to extract all readable text, splitting lines with a newline character
        all_text_nodes = main_content_container.get_text('\n', strip=True) 
        
        # Split the giant text blob into lines/paragraphs based on newlines
        full_text_lines = all_text_nodes.split('\n')
        
        article_paragraphs = []
        
        print(f"--- DEBUG: Total text lines/nodes found: {len(full_text_lines)} ---") # DEBUG LINE

        for text_line in full_text_lines:
            # Clean up: remove citation numbers and surrounding whitespace
            cleaned_text = re.sub(r'\[\d+\]', '', text_line.strip())
            
            # Filter: Use a reasonable length filter to discard short navigation/template lines
            if len(cleaned_text) > 50: 
                article_paragraphs.append(cleaned_text)
                print(f"DEBUG: Captured text snippet (Length {len(cleaned_text)}): {cleaned_text[:60]}...") # DEBUG LINE
            
        # 4. CONSOLIDATE INTO A SINGLE SEARCHABLE DOCUMENT
        article_text = ' '.join(article_paragraphs)
        
        # Get the page title
        page_title = soup.title.string.replace(' - Wikipedia', '').strip() if soup.title else 'Cat Article'
        
        # Validation check
        if len(article_text) < 1000: # Setting a high length check now that we are grabbing ALL text
             print(f"❌ Warning: Scraped content is short ({len(article_text)} chars). Scraping may have failed.")
             # We won't return here, we will still write the file to see what data was collected
        
        # Prepare the single document dictionary
        documents_to_write.append({
            'timestamp': datetime.now().isoformat(),
            'source_url': url,
            'title': page_title,
            'scraped_content': article_text 
        })
        
        # 5. WRITE DATA TO CSV
        if documents_to_write and len(article_text) > 50:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['timestamp', 'source_url', 'title', 'scraped_content'] 
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(documents_to_write)
            
            print(f"✅ Success! Article scraped (Length: {len(article_text)}). Data saved to {filename}.")
        else:
            print("⚠️ No suitable content was extracted for indexing.")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Scraping failed during request: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

# --- EXECUTION BLOCK ---
if __name__ == "__main__":
    scrape_wikipedia_cat_to_csv(SCRAPE_URL, CSV_FILENAME, HEADERS)