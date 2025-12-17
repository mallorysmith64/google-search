from flask import Flask, request, jsonify, render_template_string
from elasticsearch import Elasticsearch, helpers
from flask_cors import CORS
from dotenv import load_dotenv
import os
import csv
import importlib.util
from elasticsearch.helpers import bulk
import cloudscraper

import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
import json

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

es_client = init_elasticsearch_client()

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
    
    
    
#scrape reddit cat memes
REDDIT_INDEX_NAME = 'reddit_cat_memes_index'
REDDIT_URL = "https://www.reddit.com/r/Catmemes/"
REDDIT_CSV_FILE = "reddit_cat_memes.csv"

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
                # -----------------------------------------------------------------
                # ALL LINES BELOW MUST BE INDENTED TO BE INSIDE THE FOR LOOP!
                # -----------------------------------------------------------------
                title = post.get('title', '').strip()
                relative_url = post.get('permalink', '')
                
                if title and relative_url:
                    # 1. Clean the title of non-standard characters
                    clean_title = re.sub(r'[^\w\s\.-]', '', title).strip() 
                    
                    # Construct absolute URL
                    absolute_url = f"https://www.reddit.com{relative_url}"
                    
                    # Combine the clean title with the terms 'cat meme'
                    searchable_content = f"{clean_title} cat meme reddit" 
                    
                    documents_to_write.append({
                        'timestamp': datetime.now().isoformat(),
                        'source_url': absolute_url,
                        'title': clean_title,
                        'scraped_content': searchable_content
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

def search_reddit_memes(query, page_size=50):
    
    """
    Executes a search query against the dedicated Reddit index.
    """
    # NOTE: es_client must be initialized globally to be used here.

    
    search_body = {
        "size": page_size,
        "query": {
            # Search across title and content fields, boosting the title
            "multi_match": {
                "query": query,
                "fields": ["title^3", "scraped_content"], 
                "type": "best_fields"
            }
        }
    }
    
    try:
        res = es_client.search(
            index=REDDIT_INDEX_NAME, 
            body=search_body,
            request_timeout=30 # Add a generous timeout to ensure the query completes
        )
        
        results = []
        for hit in res['hits']['hits']:
            source = hit['_source']
            results.append({
                'title': source['title'],
                # Use scraped_content (the meme text/title) as the snippet
                'snippet': source['scraped_content'], 
                'url': source['source_url'],
                'score': hit['_score'],
                'source_type': 'Reddit Meme' # IMPORTANT for frontend differentiation
            })
        return results
    
    except Exception as e:
        print(f"Error searching Reddit index: {e}")
        return []
    
REDDIT_MAPPINGS = {
    "properties": {
        "title": {"type": "text"},
        # This maps the content from the CSV
        "scraped_content": {"type": "text"}, 
        # Source URL is typically stored as a keyword
        "source_url": {"type": "keyword"},   
    }
}
def load_reddit_data_from_csv(filename):
    """Loads documents from the Reddit CSV, mapping fields for Elasticsearch ingestion."""
    documents = []
    try:
        with open(filename, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # IMPORTANT: We use the actual column names from the scraper
                documents.append({
                    "title": row.get('title', 'Reddit Post'), 
                    "source_url": row.get('source_url', REDDIT_URL), 
                    "scraped_content": row['scraped_content'], 
                })
            print(f"✅ Loaded {len(documents)} documents from {filename} for Reddit index.")
            return documents
    except FileNotFoundError:
        print(f"🚨 CRITICAL ERROR: Scraped data file '{filename}' not found. Run /index_reddit!")
        return []
    except Exception as e:
        print(f"🚨 Error reading Reddit CSV: {e}")
        return []
    
# --------------------------------------------------------
# REDDIT INDEX SETUP ENDPOINT
# --------------------------------------------------------
@app.route('/index_reddit', methods=['POST'])
def index_reddit_data():
    """
    Creates the Reddit index, applies the mapping, runs the scraper, and bulk-ingests documents.
    """
    # NOTE: Fix the REDDIT_URL to use the JSON endpoint:
    # REDDIT_URL = "https://www.reddit.com/r/Catmemes/.json"4
    global REDDIT_URL
    
    # Check if the global variable was updated for the JSON endpoint (since the provided code was HTML-based)
    if not REDDIT_URL.endswith('.json'):
        REDDIT_URL = REDDIT_URL.strip('/') + '/.json'
        print(f"Updated REDDIT_URL to JSON endpoint: {REDDIT_URL}")

    scrape_success = scrape_reddit_cat_memes_to_csv(REDDIT_URL, REDDIT_CSV_FILE)
    if not scrape_success:
        return jsonify({"error": "Reddit Indexing aborted because web scraping failed."}), 500

    es_client = init_elasticsearch_client()
    if not es_client:
        return jsonify({"error": "Elasticsearch connection failed"}), 500

    try:
        csv_documents = load_reddit_data_from_csv(REDDIT_CSV_FILE)
        if not csv_documents:
             return jsonify({"error": f"Failed to load documents from {REDDIT_CSV_FILE}."}), 500
        
        # A. Delete/Create Index
        if es_client.indices.exists(index=REDDIT_INDEX_NAME):
            es_client.indices.delete(index=REDDIT_INDEX_NAME, ignore=[400, 404])
            print(f"Index '{REDDIT_INDEX_NAME}' deleted for fresh start.")

        es_client.indices.create(index=REDDIT_INDEX_NAME)

        # B. Add or update mappings
        es_client.indices.put_mapping(
            index=REDDIT_INDEX_NAME,
            body=REDDIT_MAPPINGS
        )

        # C. Bulk ingest documents 
        actions = [{'_index': REDDIT_INDEX_NAME, '_source': doc} for doc in csv_documents]
        print(f"Attempting to bulk ingest {len(csv_documents)} Reddit documents...")
        bulk_response = helpers.bulk(
            es_client.options(request_timeout=300),
            actions,
            refresh="wait_for" 
        )
        
        successes, errors = bulk_response
        
        if errors:
            print(f"🚨 Reddit Bulk Ingestion Errors: {len(errors)}")
            return jsonify({"error": "Reddit Bulk ingestion encountered errors."}), 500
        
        return jsonify({
            "status": f"Reddit Index created and {len(csv_documents)} documents ingested successfully",
            "bulk_stats": bulk_response
        })

    except Exception as e:
        return jsonify({"error": f"Reddit Indexing failed: {e}"}), 500
    
    # --------------------------------------------------------
# REDDIT SEARCH ENDPOINT
# --------------------------------------------------------
@app.route('/search_reddit', methods=['GET'])
def search_reddit_memes_endpoint():
    es_client = init_elasticsearch_client()
    if not es_client:
        return jsonify({"error": "Elasticsearch connection failed"}), 500

    user_query = request.args.get('q', 'funny cat')
    
    try:
        results = search_reddit_memes(user_query) # This calls your existing function
        
        return jsonify({
            "query": user_query,
            "total_hits": len(results),
            "results": results
        })

    except Exception as e:
        return jsonify({"error": f"Reddit search failed: {e}"}), 500
    
#--------------------------------------------------------
# create index for cfa breeds
#--------------------------------------------------------

# 1. Elasticsearch client initialization
CFA_INDEX_NAME = 'cat_fanciers_association_index'
CFA_URL = "https://cfa.org/breeds/"
CFA_CSV_FILE = "cfa_breeds_2025.csv"

cfa_index_body = {
    "settings": {
        "analysis": {
            "analyzer": {
                "breed_analyzer": {"type": "english"}
            }
        }
    },
    "mappings": {
        "properties": {
            "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "description": {"type": "text", "analyzer": "breed_analyzer"},
            "url": {"type": "keyword"},
            "scraped_at": {"type": "date"}
        }
    }
}

# --- SCRAPER LOGIC ---

def get_breed_links():
    """Fetches list of all breed URLs from the main CFA index page."""
    scraper = cloudscraper.create_scraper() 
    print(f"📡 Accessing CFA Index: {CFA_URL}")
    try:
        response = scraper.get(CFA_URL, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        breed_links = []
        seen_urls = set()
        
        for link in soup.find_all('a', href=True):
            url = link['href']
            name = link.get_text(strip=True)
            # Filter for specific breed profile URLs
            if "cfa.org" in url and len(url.split('/')) >= 4:
                if not any(x in url.lower() for x in ['contact', 'about', 'privacy', 'tag', 'category']):
                    if name and url not in seen_urls:
                        breed_links.append({'name': name, 'url': url})
                        seen_urls.add(url)
        print(f"✅ Found {len(breed_links)} unique breeds.")
        return breed_links
    except Exception as e:
        print(f"⚠️ Link Scrape Error: {e}")
        return []

def upload_cfa_to_es(breed_links, index_name):
    """Visits each breed URL to get detailed descriptions and bulk uploads to ES."""
    scraper = cloudscraper.create_scraper()
    actions = []
    
    for i, breed in enumerate(breed_links):
        print(f"  [{i+1}/{len(breed_links)}] Scraping: {breed['name']}")
        try:
            res = scraper.get(breed['url'], timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            # Targets the main text content area
            content = soup.find('div', class_='entry-content') or soup.find('main')
            paragraphs = content.find_all('p')
            desc = " ".join([p.get_text(strip=True) for p in paragraphs[:5]])
        except Exception:
            desc = "Description currently unavailable."

        actions.append({
            "_index": index_name,
            "_id": breed['url'],
            "_source": {
                "name": breed['name'],
                "url": breed['url'],
                "description": desc,
                "scraped_at": datetime.now().isoformat()
            }
        })
        time.sleep(0.3) # Polite delay
    
    if actions:
        successes, _ = helpers.bulk(es_client, actions)
        return successes
    return 0

# --- FLASK ROUTES ---

@app.route('/index_cfa', methods=['POST'])
def index_cfa_data():
    if not es_client:
        return jsonify({"error": "Elasticsearch not connected"}), 500
    
    print("--- 📡 STEP 1: Fetching Links from CFA ---")
    links = get_breed_links()
    
    if not links:
        print("❌ CRITICAL: No links found. CFA might be blocking the request.")
        return jsonify({"error": "No breed links found. Check terminal logs."}), 500

    print(f"✅ Found {len(links)} links. Proceeding to create index...")

    try:
        if es_client.indices.exists(index=CFA_INDEX_NAME):
            es_client.indices.delete(index=CFA_INDEX_NAME)
        
        es_client.indices.create(index=CFA_INDEX_NAME, body=cfa_index_body)
    except Exception as e:
        return jsonify({"error": f"Index creation failed: {e}"}), 500
    
    print("--- 📥 STEP 2: Scraping Details & Ingesting to ES ---")
    count = upload_cfa_to_es(links, CFA_INDEX_NAME)
    print(f"🎉 SUCCESS: Indexed {count} breeds.")
    
    return jsonify({
        "status": "success", 
        "message": f"Scraped and indexed {count} breeds from CFA."
    })

@app.route('/search_cfa', methods=['GET'])
def search_cfa():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    try:
        res = es_client.search(index=CFA_INDEX_NAME, body={
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["name^5", "description"],
                    "type": "best_fields",
                    "fuzziness": "AUTO" # This helps if you search "breeds" vs "breed"
                }
            }
        })
        results = [hit['_source'] for hit in res['hits']['hits']]
        return jsonify(results)
    except Exception as e:
        return jsonify([])

@app.route('/api/search_all', methods=['GET'])
def search_all():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"breeds": [], "facts": [], "memes": []})

    # Optimized CFA Search
    try:
        breed_res = es_client.search(index=CFA_INDEX_NAME, body={
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["name^5", "description"], # Priority on Name
                    "fuzziness": "AUTO",                 # Handles minor typos
                    "type": "best_fields"
                }
            }
        })
        # Debug: Print to terminal to see if ES is actually returning anything
        print(f"CFA Results found: {breed_res['hits']['total']['value']}")
        breeds = [hit['_source'] for hit in breed_res['hits']['hits']]
    except Exception as e:
        print(f"Error searching CFA index: {e}")
        breeds = []

    # Facts search (uses the Wikipedia/article index)
    facts = []
    try:
        if es_client.indices.exists(index=INDEX_NAME):
            facts_res = es_client.search(
                index=INDEX_NAME,
                body={
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^3", "body_text", "snippet"],
                            "type": "best_fields"
                        }
                    },
                    "size": 5,
                    "_source": ["title", "url", "snippet", "body_text"]
                }
            )
            facts = [hit['_source'] for hit in facts_res['hits']['hits']]
    except Exception as e:
        print(f"Error searching facts index: {e}")
        facts = []

    # 3. Search Reddit Memes
    memes = search_reddit_memes(query)

    return jsonify({
        "breeds": breeds,
        "facts": facts,
        "memes": memes
    })
    
@app.route('/debug_cfa', methods=['GET'])
def debug_cfa():
    try:
        # Ask ES for every document in the CFA index
        res = es_client.search(index=CFA_INDEX_NAME, body={"query": {"match_all": {}}, "size": 10})
        count = es_client.count(index=CFA_INDEX_NAME)['count']
        
        return jsonify({
            "total_documents_in_index": count,
            "sample_data": [hit['_source'] for hit in res['hits']['hits']]
        })
    except Exception as e:
        return jsonify({"error": str(e)})
if __name__ == '__main__':
    app.run(debug=True, port=5000)
    