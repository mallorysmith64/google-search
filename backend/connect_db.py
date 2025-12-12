from flask import Flask, request, jsonify, render_template_string
from elasticsearch import Elasticsearch, helpers
from flask_cors import CORS
from dotenv import load_dotenv
import os
import csv
import importlib.util

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)
load_dotenv()

# Attempt to import mapping_data; provide sensible defaults if not found
spec = importlib.util.find_spec("mapping_data")
# ... (The rest of the mapping_data import logic remains the same) ...
if spec is not None:
    mapping_data = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mapping_data)
    INDEX_NAME = getattr(mapping_data, "INDEX_NAME", "search-index")
    MAPPINGS = getattr(mapping_data, "MAPPINGS", {
        "properties": {
            "url": {"type": "keyword"},
            "title": {"type": "text"},
            "snippet": {"type": "text"},
            "body_text": {"type": "text"}
        }
    })
    documents = getattr(mapping_data, "documents", [
        {
            "title": "Yosemite National Park",
            "body_text": "Yosemite is famous for its granite cliffs and waterfalls.",
            "url": "https://example.org/yosemite",
            "snippet": "Famous for El Capitan and Half Dome."
        },
        {
            "title": "Yellowstone National Park",
            "body_text": "Yellowstone is known for geothermal features and wildlife.",
            "url": "https://example.org/yellowstone",
            "snippet": "Home to Old Faithful and large bison herds."
        }
    ])
else:
    # Fallback defaults for local development or when mapping_data.py is missing.
    INDEX_NAME = "search_index"
    MAPPINGS = {
        "properties": {
            "title": {"type": "text"},
            "body_text": {"type": "text"},
            "url": {"type": "keyword"},
            "snippet": {"type": "text"}
        }
    }
    documents = [
        {
            "title": "Yosemite National Park",
            "body_text": "Yosemite is famous for its granite cliffs and waterfalls.",
            "url": "https://example.org/yosemite",
            "snippet": "Famous for El Capitan and Half Dome."
        },
        {
            "title": "Yellowstone National Park",
            "body_text": "Yellowstone is known for geothermal features and wildlife.",
            "url": "https://example.org/yellowstone",
            "snippet": "Home to Old Faithful and large bison herds."
        }
    ]

# --- MODIFIED: USE THE CORRECT FILENAME FOR THE SCRAPER ---
CSV_FILENAME = "britannica_cat_data.csv"
# --------------------------------------------------------------------------------------
# 1. Configuration (REPLACE WITH YOUR ACTUAL CREDENTIALS) - REMAINS THE SAME
# --------------------------------------------------------------------------------------
ELASTIC_HOST_URL = os.getenv("ELASTIC_HOST_URL")
ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY")
client = None

def init_elasticsearch_client():
    global client
    if client is None:
        full_host_url = f"https://{ELASTIC_HOST_URL}"
        try:
            client = Elasticsearch(
                [full_host_url],
                api_key=ELASTIC_API_KEY
            )
            if client.ping():
                print("Successfully connected to Elasticsearch.")
            else:
                print("Connection failed, check credentials.")
                client = None
        except Exception as e:
            print(f"Error initializing Elasticsearch client: {e}")
            client = None
    return client

init_elasticsearch_client()

# --------------------------------------------------------
# Web Scraping Function
# --------------------------------------------------------
SCRAPE_URL = "https://www.britannica.com/animal/cat"

def scrape_and_save_csv(url, filename):
    """
    Scrapes the specified URL, extracts the main text, and saves it to a CSV file.
    This replaces the previous standalone scraping script.
    """
    print(f"--- STARTING SCRAPE: {url} ---")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Target the main content area (based on previous successful scrape)
        main_content_container = soup.find('div', class_='topic-content')
        if not main_content_container:
            main_content_container = soup.find('div', id='content')
            if not main_content_container:
                print("❌ Main content container not found.")
                return False

        paragraphs = main_content_container.find_all('p')
        full_text = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text:
                cleaned_text = re.sub(r'\s+', ' ', text).strip()
                full_text.append(cleaned_text)

        article_text = ' '.join(full_text)
        page_title = soup.title.string.replace('| Britannica', '').strip() if soup.title else 'Cat Article'
        
        # Data structure must match what load_data_from_csv expects
        data_to_write = {
            'timestamp': datetime.now().isoformat(),
            'source_url': url,
            'title': page_title,
            # Use 'scraped_content' as the column name to match the scraper output
            'scraped_content': article_text 
        }
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = data_to_write.keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerow(data_to_write)
        
        print(f"✅ Successfully scraped data and saved to {filename}. Content length: {len(article_text)}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching the URL: {e}")
    except Exception as e:
        print(f"❌ An error occurred during scraping: {e}")
    return False

# --------------------------------------------------------
# Index Setup Endpoint
# --------------------------------------------------------
@app.route('/index_data', methods=['POST'])
def index_data():
    """
    Creates the index, applies the mapping, runs the scraper, and bulk-ingests documents.
    """
    # 1. RUN THE SCRAPER BEFORE ANYTHING ELSE
    scrape_success = scrape_and_save_csv(SCRAPE_URL, CSV_FILENAME)
    if not scrape_success:
        return jsonify({"error": "Indexing aborted because web scraping failed."}), 500

    es_client = init_elasticsearch_client()
    if not es_client:
        return jsonify({"error": "Elasticsearch connection failed"}), 500

    try:
        csv_documents = load_data_from_csv(CSV_FILENAME)
        if not csv_documents:
             return jsonify({"error": f"Failed to load documents from {CSV_FILENAME}. Check file path and contents."}), 500
        
        # A. Create or verify index existence (Remaining logic is the same)
        if es_client.indices.exists(index=INDEX_NAME):
            es_client.indices.delete(index=INDEX_NAME, ignore=[400, 404])
            print(f"Index '{INDEX_NAME}' deleted for fresh start.")

        create_response = es_client.indices.create(index=INDEX_NAME)
        print("Index created:", create_response)

        # B. Add or update mappings
        mapping_response = es_client.indices.put_mapping(
            index=INDEX_NAME,
            body=MAPPINGS
        )
        print("Mappings updated:", mapping_response)

        # C. Bulk ingest documents 
        ingestion_timeout=300 
        actions = [{'_index': INDEX_NAME, '_source': doc} for doc in csv_documents]
        bulk_response = helpers.bulk(
            es_client.options(request_timeout=ingestion_timeout),
            actions,
            refresh="wait_for" 
        )
        
        return jsonify({
            "status": f"Index created and {len(csv_documents)} documents from CSV ingested successfully",
            "bulk_stats": bulk_response
        })

    except Exception as e:
        return jsonify({"error": f"Indexing failed: {e}"}), 500

# --------------------------------------------------------
# Search Endpoint
# --------------------------------------------------------
@app.route('/search', methods=['GET'])
def search_engine():
    es_client = init_elasticsearch_client()
    if not es_client:
        return jsonify({"error": "Elasticsearch connection failed"}), 500

    user_query = request.args.get('q', 'Sierra Nevada')
    
    search_body = {
        "query": {
            "multi_match": {
                "query": user_query,
                "fields": ["title^10", "body_text^5"], 
                "type": "best_fields"
            }
        },
        "size": 10,
        "_source": ["title", "url", "snippet"]
    }

    try:
        search_response = es_client.search(
            index=INDEX_NAME,
            body=search_body,
        )

        results = []
        for hit in search_response['hits']['hits']:
            # IMPORTANT: Add the unique Elasticsearch ID (_id) to the result object
            results.append({
                "id": hit['_id'], # <<<--- ADD THIS LINE
                "score": round(hit['_score'], 2),
                "title": hit['_source'].get('title'),
                "url": hit['_source'].get('url'),
                "snippet": hit['_source'].get('snippet')
            })

        return jsonify({
            "query": user_query,
            "total_hits": search_response['hits']['total']['value'],
            "results": results
        })

    except Exception as e:
        return jsonify({"error": f"Search failed: {e}"}), 500

# --------------------------------------------------------
# 5. Simple Web Interface
# --------------------------------------------------------
@app.route('/', methods=['GET'])
def home_page():
    # ... (home_page function remains the same) ...
    html_template = """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <title>Elastic Search Demo</title>
        <style>
            body { font-family: sans-serif; padding: 20px; max-width: 800px; margin: auto; }
            h1 { color: #0056b3; }
            form { margin-bottom: 30px; }
            input[type="text"] { width: 70%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; }
            input[type="submit"] { padding: 10px 15px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
            .result-container { margin-top: 20px; border-top: 1px solid #eee; padding-top: 15px; }
            .result-item { margin-bottom: 25px; }
            .result-title { font-size: 1.2em; color: #1a0dab; text-decoration: underline; margin-bottom: 5px; }
            .result-url { color: #006621; font-size: 0.9em; margin-bottom: 3px; }
            .result-snippet { color: #545454; }
        </style>
    </head>
    <body>
        <h1>National Parks Search Engine</h1>
        <form action="/search" method="get">
            <input type="text" name="q" placeholder="Search for wildlife or features..." required>
            <input type="submit" value="Search">
        </form>

        <h2>Instructions:</h2>
        <ol>
            <li>Ensure Flask is running.</li>
            <li><strong>First, run the indexing endpoint once (e.g., using a tool like Postman):</strong> <code>POST /index_data</code></li>
            <li>Then, use the search form above or call the endpoint: <code>GET /search?q=bears+and+elk</code></li>
        </ol>
    </body>
    </html>
    """
    return render_template_string(html_template)

# --------------------------------------------------------
# 6. CSV Loading Function (MODIFIED TO USE CORRECT COLUMNS)
# --------------------------------------------------------

def load_data_from_csv(filename):
    """
    Reads data from the scraped CSV and formats it for Elasticsearch bulk ingestion.
    """
    documents = []
    try:
        with open(filename, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # The columns produced by the scraper are: 
            # 'timestamp', 'source_url', 'title', 'scraped_content'
            
            for row in reader:
                # Check for the column generated by the scraper
                if 'scraped_content' in row:
                    documents.append({
                        "title": row.get('title', 'Britannica Article'), # Use the scraped title
                        "url": row.get('source_url', 'https://www.britannica.com'), # Use the scraped URL
                        "body_text": row['scraped_content'], 
                        "snippet": row['scraped_content'][:200].strip() + "..." 
                    })
                else:
                    print(f"🚨 Skipping row: 'scraped_content' column not found in CSV row: {row.keys()}")
            
        print(f"✅ Loaded {len(documents)} documents from {filename}.")
        return documents

    except FileNotFoundError:
        print(f"🚨 CRITICAL ERROR: Scraped data file '{filename}' not found. Run /index_data!")
        return []
    except Exception as e:
        print(f"🚨 Error reading CSV: {e}")
        return []
    
# 5. Diagnostic Endpoint (NEW ADDITION)
# --------------------------------------------------------
@app.route('/check_content', methods=['GET'])
def check_content():
    """
    Fetches the first document from the index to verify content and structure.
    """
    es_client = init_elasticsearch_client()
    if not es_client:
        return jsonify({"error": "Elasticsearch connection failed"}), 500

    try:
        # Fetch the first document only, sorted by insertion time (approx)
        response = es_client.search(
            index=INDEX_NAME,
            body={
                "query": {"match_all": {}},
                "size": 1,
                "_source": ["title", "body_text"] # Only fetch the fields we care about
            }
        )

        hits = response['hits']['hits']
        if not hits:
            return jsonify({
                "status": "Index is empty",
                "message": f"Index '{INDEX_NAME}' contains 0 documents. Please run POST /index_data."
            })
            
        first_doc = hits[0]['_source']
        
        # Check if the required fields are present
        if 'body_text' not in first_doc:
            return jsonify({
                "status": "Error in Document Structure",
                "message": "The indexed document does not contain the 'body_text' field.",
                "doc_keys": list(first_doc.keys())
            })
            
        # Analyze the body_text for keywords
        body_text = first_doc['body_text']
        
        return jsonify({
            "status": "Success - Content Verified",
            "title": first_doc.get('title', 'N/A'),
            "body_text_length": len(body_text),
            "body_text_snippet": body_text[:500] + "...",
            "contains_cat": "cat" in body_text.lower(),
            "contains_feline": "feline" in body_text.lower(),
            "IMPORTANT": "If 'contains_cat' or 'contains_feline' is False, the SCRAPING failed to grab the content."
        })

    except Exception as e:
        return jsonify({"error": f"Diagnostic check failed: {e}"}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)