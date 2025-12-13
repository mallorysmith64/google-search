# reddit_cat_memes_webscraper.py

import csv
import requests # We will use this instead of Playwright
from datetime import datetime
import time # For polite scraping delay
import json
import os
# We keep BeautifulSoup and Playwright imports commented out as they are no longer needed
# from playwright.sync_api import sync_playwright 
# from bs4 import BeautifulSoup 

# --- CONFIGURATION ---
# Append .json to the URL to hit the unofficial JSON endpoint
REDDIT_URL = "https://www.reddit.com/r/Catmemes/.json?limit=100" 
REDDIT_CSV_FILENAME = "reddit_cat_memes.csv"

def scrape_reddit_cat_memes_to_csv(url, filename):
    """
    Scrapes Reddit using the stable, unofficial JSON endpoint via requests.
    """
    print(f"--- Starting JSON endpoint scrape for: {url} ---")
    documents_to_write = []
    
    # Reddit expects a User-Agent string to not block requests
    headers = {
        'User-Agent': 'Simple-Python-Scraper-V1.0 (by marssmith)'
    }
    
    try:
        # 1. Make the request
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
        
        data = response.json()
        
        # 2. Parse the JSON structure
        if 'data' in data and 'children' in data['data']:
            posts = data['data']['children']
            print(f"--- DEBUG: Found {len(posts)} posts in the JSON response. ---")
            
            for post_item in posts:
                post = post_item['data']
                
                # Extracting necessary fields from the JSON
                title = post.get('title', '').strip()
                relative_url = post.get('permalink', '')
                
                if title and relative_url:
                    # Construct absolute URL
                    absolute_url = f"https://www.reddit.com{relative_url}"
                    
                    documents_to_write.append({
                        'timestamp': datetime.now().isoformat(),
                        'source_url': absolute_url,
                        'title': title,
                        'scraped_content': title # Use title as the content/snippet
                    })

            # 3. WRITE DATA TO CSV
            if documents_to_write:
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['timestamp', 'source_url', 'title', 'scraped_content'] 
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(documents_to_write)
                
                print(f"✅ Success! Found {len(documents_to_write)} posts. Data saved to {filename}.")
                return True
            else:
                print("⚠️ JSON endpoint returned no posts.")
                return False

        else:
            print("⚠️ JSON structure was unexpected. Could not find posts in 'data.children'.")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP Request failed: {e}")
        return False
    except json.JSONDecodeError:
        print("❌ Failed to decode JSON response.")
        print(f"Response Text Sample: {response.text[:200]}...")
        return False
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        return False

# If you run this file directly, it will execute the scraper
if __name__ == '__main__':
    # Add a small delay for politeness if running standalone
    time.sleep(1) 
    if scrape_reddit_cat_memes_to_csv(REDDIT_URL, REDDIT_CSV_FILENAME):
        print(f"\nStandalone scrape complete. Check {REDDIT_CSV_FILENAME}")
    else:
        print("\nStandalone scrape failed.")