import requests
from bs4 import BeautifulSoup
import csv
import re
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse # Helper for extracting domain

# New Britannica URL
url = "https://www.britannica.com"
filename = "britannica_news.csv"
YOUR_USER_AGENT = 'MyAwesomeCrawler/1.0 (+https://example.com/)' # IMPORTANT: Use your unique User-Agent

# Essential header to prevent 403 Forbidden error
HEADERS = {
    'User-Agent': YOUR_USER_AGENT
}

def check_robots_txt_permission(target_url, user_agent):
    """
    Checks if the specified user_agent is allowed to fetch the target_url
    according to the site's robots.txt file.
    """
    try:
        # 1. Determine the robots.txt URL
        parsed_url = urlparse(target_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        robots_txt_url = base_url + "/robots.txt"

        # 2. Initialize and read the parser
        rp = RobotFileParser()
        rp.set_url(robots_txt_url)
        # Attempt to read the robots.txt file. This performs an HTTP request.
        rp.read() 

        # 3. Check permission
        if rp.can_fetch(user_agent, target_url):
            print(f"✅ robots.txt check: User-Agent '{user_agent}' **is allowed** to access this URL.")
            return True
        else:
            print(f"🛑 robots.txt check: User-Agent '{user_agent}' **is disallowed** from accessing this URL.")
            return False

    except Exception as e:
        # Handle cases where robots.txt is inaccessible (e.g., 404, DNS error).
        # Standard convention is to assume permission if robots.txt cannot be found.
        print(f"⚠️ Could not check robots.txt (Error: {e}). Assuming permission to proceed, but you should handle this case carefully.")
        return True

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