import requests
from bs4 import BeautifulSoup
import csv
import re

# New Britannica URL
url = "https://www.britannica.com/animal/cat"
filename = "britannica_cat_data.csv"

# Essential header to prevent 403 Forbidden error
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def scrape_britannica_to_csv(url, filename, headers):
    """
    Scrapes the Britannica article on 'Cat' for all paragraphs and writes them to a CSV.
    """
    try:
        # 1. Fetch the content using the User-Agent header
        response = requests.get(url, headers=headers)
        response.raise_for_status() 
        
        soup = BeautifulSoup(response.text, 'html.parser')
        data_rows = []
        
        # 2. Target the main content area (Britannica often uses <article> or a general container)
        # For simplicity, we'll find all paragraphs in the document.
        # In a real-world scenario, you might target a class like 'topic-content' or similar.
        all_paragraphs = soup.find_all('p')
        
        # 3. Process the paragraphs
        for i, p_tag in enumerate(all_paragraphs):
            # Exclude very short paragraphs (often image captions or footers)
            if len(p_tag.text.strip()) > 50: 
                # Clean up text: remove reference numbers and leading/trailing whitespace
                cleaned_text = re.sub(r'\[\d+\]', '', p_tag.text.strip())
                
                data_rows.append({
                    'Paragraph_Number': i + 1,
                    'Content': cleaned_text
                })

        # 4. Write Data to CSV
        if data_rows:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Paragraph_Number', 'Content']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data_rows)
            
            print(f"✅ Successfully scraped **{len(data_rows)}** paragraphs and saved data to **{filename}**")
        else:
            print("⚠️ Could not find any suitable paragraphs to write.")

    except requests.exceptions.HTTPError as e:
        print(f"❌ Scraping failed. Status Code: {response.status_code}. If 403, try changing the User-Agent.")
    except requests.exceptions.RequestException as e:
        print(f"❌ An error occurred during the request: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

# Run the function
scrape_britannica_to_csv(url, filename, HEADERS)