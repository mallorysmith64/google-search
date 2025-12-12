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

# --- MAPPING DATA SETUP (Cleaned to be minimal and correct) ---
INDEX_NAME = "search_index"
# NOTE: These MAPPINGS are defined here, but the active index uses the old/inferred ones.
# We keep these definitions because the /index_data route will delete the old index
# and apply these correct ones for future use.
MAPPINGS = {
    "properties": {
        "title": {"type": "text"},
        "body_text": {"type": "text"}, 
        "url": {"type": "keyword"},   
        "snippet": {"type": "text"}
    }
}

# --- WIKIPEDIA SCRAPER CONFIGURATION ---
SCRAPE_URL = "https://en.wikipedia.org/w/index.php?title=Cat&action=render"
CSV_FILENAME = "wikipedia_cat_data.csv"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- ELASTICSEARCH CLIENT INIT ---
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

# --- SCRAPER FUNCTION (Brute-Force Text Extraction) ---
def scrape_wikipedia_cat_to_csv(url, filename, headers):
    print(f"--- Starting Wikipedia scrape for: {url} ---")
    documents_to_write = [] 

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() 

        soup = BeautifulSoup(response.content, 'html.parser')
        main_content_container = soup.find('body')
        if not main_content_container:
            main_content_container = soup
        
        all_text_nodes = main_content_container.get_text('\n', strip=True) 
        full_text_lines = all_text_nodes.split('\n')
        article_paragraphs = []
        
        print(f"--- DEBUG: Total text lines/nodes found: {len(full_text_lines)} ---") 

        for text_line in full_text_lines:
            cleaned_text = re.sub(r'\[\d+\]', '', text_line.strip())
            if len(cleaned_text) > 50: 
                article_paragraphs.append(cleaned_text)
            
        article_text = ' '.join(article_paragraphs)
        page_title = soup.title.string.replace(' - Wikipedia', '').strip() if soup.title else 'Cat Article'
        
        if len(article_text) < 1000: 
             print(f"❌ Warning: Scraped content is short ({len(article_text)} chars). Scraping may have failed.")
        
        # NOTE: This creates the CSV columns: 'source_url', 'title', 'scraped_content'
        documents_to_write.append({
            'timestamp': datetime.now().isoformat(),
            'source_url': url,
            'title': page_title,
            'scraped_content': article_text 
        })
        
        if documents_to_write and len(article_text) > 50:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['timestamp', 'source_url', 'title', 'scraped_content'] 
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(documents_to_write)
            
            print(f"✅ Success! Article scraped (Length: {len(article_text)}). Data saved to {filename}.")
            return True
        else:
            print("⚠️ No suitable content was extracted for indexing.")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Scraping failed during request: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
    return False

# --- CSV LOADER FUNCTION (Remains mapping to 'body_text' for bulk ingestion) ---
def load_data_from_csv(filename):
    documents = []
    try:
        with open(filename, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if 'scraped_content' in row:
                    documents.append({
                        # The fields below are the PREFERRED fields for the MAPPINGS defined above
                        "title": row.get('title', 'Wikipedia Article'), 
                        "url": row.get('source_url', SCRAPE_URL), 
                        "body_text": row['scraped_content'], 
                        "snippet": row['scraped_content'][:200].strip() + "..." 
                    })
            print(f"✅ Loaded {len(documents)} documents from {filename}.")
            return documents
    except FileNotFoundError:
        print(f"🚨 CRITICAL ERROR: Scraped data file '{filename}' not found. Run /index_data!")
        return []
    except Exception as e:
        print(f"🚨 Error reading CSV: {e}")
        return []

# --------------------------------------------------------
# INDEX SETUP ENDPOINT (FIXED: Added robust error checking)
# --------------------------------------------------------
@app.route('/index_data', methods=['POST'])
def index_data():
    """
    Creates the index, applies the mapping, runs the scraper, and bulk-ingests documents.
    """
    scrape_success = scrape_wikipedia_cat_to_csv(SCRAPE_URL, CSV_FILENAME, HEADERS)
    if not scrape_success:
        return jsonify({"error": "Indexing aborted because web scraping failed."}), 500

    es_client = init_elasticsearch_client()
    if not es_client:
        return jsonify({"error": "Elasticsearch connection failed"}), 500

    try:
        csv_documents = load_data_from_csv(CSV_FILENAME)
        if not csv_documents:
             return jsonify({"error": f"Failed to load documents from {CSV_FILENAME}. Check file path and contents."}), 500
        
        # A. Delete/Create Index
        if es_client.indices.exists(index=INDEX_NAME):
            # FORCING DELETION TO RESOLVE MAPPING INCOMPATIBILITIES
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
        
        print(f"Attempting to bulk ingest {len(csv_documents)} documents...")
        bulk_response = helpers.bulk(
            es_client.options(request_timeout=ingestion_timeout),
            actions,
            refresh="wait_for" 
        )
        
        successes, errors = bulk_response
        
        if errors:
            print("\n🚨 CRITICAL BULK INGESTION ERRORS FOUND:")
            print(f"  Total Errors: {len(errors)}")
            print(f"  Sample Error (First 500 chars): {str(errors[0])[:500]}...") 
            return jsonify({
                "error": "Bulk ingestion encountered errors (check server log for the full error details).",
                "success_count": successes,
                "error_count": len(errors),
                "sample_error": errors[0] if errors else None
            }), 500
        
        return jsonify({
            "status": f"Index created and {len(csv_documents)} documents from CSV ingested successfully",
            "bulk_stats": bulk_response
        })

    except Exception as e:
        return jsonify({"error": f"Indexing failed: {e}"}), 500

# --------------------------------------------------------
# SEARCH ENDPOINT (FIXED: To search using the preferred field names: body_text, url, snippet)
# --------------------------------------------------------
@app.route('/search', methods=['GET'])
def search_engine():
    es_client = init_elasticsearch_client()
    if not es_client:
        return jsonify({"error": "Elasticsearch connection failed"}), 500

    user_query = request.args.get('q', 'cat feline')
    
    # We now search the 'body_text' field, which is the preferred field name defined in MAPPINGS.
    # If the user runs /index_data, this search will work.
    search_body = {
        "query": {
            "match": {
                "body_text": {
                    "query": user_query,
                    "operator": "and"
                }
            }
        },
        "size": 10,
        "_source": ["title", "url", "snippet", "body_text"] # Retrieve all preferred fields
    }

    try:
        search_response = es_client.search(
            index=INDEX_NAME,
            body=search_body,
        )

        results = []
        for hit in search_response['hits']['hits']:
            # The data processing now relies on the MAPPINGS being correct (body_text, url, snippet)
            # which is guaranteed after running /index_data successfully.
            results.append({
                "id": hit['_id'],
                "score": round(hit['_score'], 2),
                "title": hit['_source'].get('title'),
                "url": hit['_source'].get('url'),
                "snippet": hit['_source'].get('snippet') or hit['_source'].get('body_text', '')[:200].strip() + "..."
            })

        return jsonify({
            "query": user_query,
            "total_hits": search_response['hits']['total']['value'],
            "results": results
        })

    except Exception as e:
        return jsonify({"error": f"Search failed: {e}"}), 500

# --------------------------------------------------------
# REMAINING ENDPOINTS (Home, Check_Content)
# --------------------------------------------------------
@app.route('/', methods=['GET'])
def home_page():
    html_template = """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <title>Wikipedia Cat Search Demo</title>
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
        <h1>Wikipedia Cat Article Search Engine</h1>
        <form action="/search" method="get">
            <input type="text" name="q" placeholder="Search for taxonomy, species, or domestic cat..." required>
            <input type="submit" value="Search">
        </form>

        <h2>Instructions:</h2>
        <ol>
            <li>Ensure Flask and Elasticsearch are running.</li>
            <li><strong>First, run the indexing endpoint (using Postman/cURL):</strong> <code>POST /index_data</code></li>
            <li>Then, use the search form above or call the endpoint: <code>GET /search?q=feline+species</code></li>
        </ol>
        
        <h3>Diagnostic Endpoints:</h3>
        <ul>
            <li><a href="/check_content">/check_content</a> (Verify if data was successfully indexed)</li>
        </ul>
    </body>
    </html>
    """
    return render_template_string(html_template)

@app.route('/check_content', methods=['GET'])
def check_content():
    es_client = init_elasticsearch_client()
    if not es_client:
        return jsonify({"error": "Elasticsearch connection failed"}), 500

    try:
        response = es_client.search(
            index=INDEX_NAME,
            body={
                "query": {"match_all": {}},
                "size": 1,
                "_source": ["title", "body_text"]
            }
        )

        hits = response['hits']['hits']
        if not hits:
            return jsonify({
                "status": "Index is empty",
                "message": f"Index '{INDEX_NAME}' contains 0 documents. Please run POST /index_data."
            })
            
        first_doc = hits[0]['_source']
        body_text = first_doc.get('body_text', 'No body_text field found')
        
        return jsonify({
            "status": "Success - Content Verified",
            "title": first_doc.get('title', 'N/A'),
            "body_text_length": len(body_text),
            "body_text_snippet": body_text[:500] + "...",
            "contains_cat": "cat" in body_text.lower(),
            "contains_feline": "feline" in body_text.lower(),
            "IMPORTANT": "The length should be high (10k+) and both keywords should be True."
        })

    except Exception as e:
        return jsonify({"error": f"Diagnostic check failed: {e}"}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)