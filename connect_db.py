from flask import Flask, request, jsonify, render_template_string
from elasticsearch import Elasticsearch, helpers
from flask_cors import CORS
from dotenv import load_dotenv
import os
import csv
import importlib.util

app = Flask(__name__)

# 2. Add this line immediately after app = Flask(__name__)
# This is the easiest way: it allows ALL origins (*) to access ALL routes.
CORS(app)

load_dotenv()

# Attempt to import mapping_data; provide sensible defaults if not found

spec = importlib.util.find_spec("mapping_data")
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
    
CSV_FILENAME = "britannica_news.csv"
# --------------------------------------------------------
# 1. Configuration (REPLACE WITH YOUR ACTUAL CREDENTIALS)
# --------------------------------------------------------
# Use the "Deployment ID" (the full, long string you copied) here.
# This variable is your ELASTIC_CLOUD_ID.
ELASTIC_HOST_URL = os.getenv("ELASTIC_HOST_URL")
# Your API Key, which you generate on the same page as the Deployment ID.
ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY")

client = None

def init_elasticsearch_client():
    """Initializes and returns the global Elasticsearch client."""
    global client
    if client is None:
        full_host_url = f"https://{ELASTIC_HOST_URL}"
        try:
            # The Elasticsearch client uses the Cloud ID to figure out the
            # hostname and port, making the connection simple and reliable.
            client = Elasticsearch(
                [full_host_url],
                api_key=ELASTIC_API_KEY
            )
            # Check connection by pinging
            if client.ping():
                print("Successfully connected to Elasticsearch.")
            else:
                print("Connection failed, check credentials.")
                client = None
        except Exception as e:
            print(f"Error initializing Elasticsearch client: {e}")
            client = None
    return client

# Initialize client on startup
init_elasticsearch_client()

# --------------------------------------------------------
# 2. Index Setup Endpoint (RUN THIS ONCE)
# --------------------------------------------------------
@app.route('/index_data', methods=['POST'])
def index_data():
    """
    Creates the index, applies the 'Google-like' mapping, and bulk-ingests documents.
    Run this endpoint only once when setting up your application.
    """
    es_client = init_elasticsearch_client()
    if not es_client:
        return jsonify({"error": "Elasticsearch connection failed"}), 500

    try:
        csv_documents = load_data_from_csv(CSV_FILENAME)
        if not csv_documents:
             return jsonify({"error": f"Failed to load documents from {CSV_FILENAME}. Check file path and contents."}), 500
        # A. Create or verify index existence
        if es_client.indices.exists(index=INDEX_NAME):
            # For simplicity, we delete and recreate to ensure the new mapping is applied
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

        # C. Bulk ingest documents (allowing time for semantic model loading)
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
# 3. Search Endpoint (The Core Functionality)
# --------------------------------------------------------
@app.route('/search', methods=['GET'])
def search_engine():
    """
    Performs a semantic search on the indexed data.
    Usage: /search?q=your+query+here
    """
    es_client = init_elasticsearch_client()
    if not es_client:
        return jsonify({"error": "Elasticsearch connection failed"}), 500

    # Get query string from URL parameters (e.g., ?q=hiking trails)
    user_query = request.args.get('q', 'Sierra Nevada') # Default query for testing
    
    # -----------------------------
    # Define the Search Query (Semantic + Keyword)
    # -----------------------------
    # We combine traditional keyword search on 'title' with semantic search on 'body_text'.
    search_body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "semantic": {
                            "field": "body_text",
                            "query": user_query
                        }
                    }
                ],
                # Optional: Add a standard keyword match for better recall on titles
                "should": [
                    {
                        "match": {
                            "title": {
                                "query": user_query,
                                "boost": 2 # Boost title matches to make them more relevant
                            }
                        }
                    }
                ]
            }
        },
        "size": 10,
        "_source": ["title", "url", "snippet"] # Only retrieve the fields we need for display
    }

    try:
        search_response = es_client.search(
            index=INDEX_NAME,
            body=search_body,
        )

        results = []
        for hit in search_response['hits']['hits']:
            # The search results now look like a typical Google snippet
            results.append({
                "score": round(hit['_score'], 2),
                "title": hit['_source'].get('title'),
                "url": hit['_source'].get('url'),
                "snippet": hit['_source'].get('snippet')
            })

        # Return results as JSON or a simple HTML page
        return jsonify({
            "query": user_query,
            "total_hits": search_response['hits']['total']['value'],
            "results": results
        })

    except Exception as e:
        return jsonify({"error": f"Search failed: {e}"}), 500

# --------------------------------------------------------
# 4. Simple Web Interface (Optional but helpful for testing)
# --------------------------------------------------------
@app.route('/', methods=['GET'])
def home_page():
    """A simple form to test the search endpoint."""
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

#put csv into elasticsearch
url = "https://www.britannica.com"

def load_data_from_csv(filename):
    """
    Reads data from the scraped CSV and formats it for Elasticsearch bulk ingestion.
    """
    documents = []
    try:
        with open(filename, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                # IMPORTANT: Verify that 'Content' is the correct column header from your CSV
                if 'Content' in row:
                    documents.append({
                        "title": "Britannica",
                        "url": url,
                        "body_text": row['Content'], 
                        "snippet": row['Content'][:200].strip() + "..." 
                    })
                else:
                    print(f"🚨 Skipping row: 'Content' column not found in CSV row: {row.keys()}")
            
        print(f"✅ Loaded {len(documents)} documents from {filename}.")
        return documents

    except FileNotFoundError:
        # 🔑 This is the key error check
        print(f"🚨 CRITICAL ERROR: Scraped data file '{filename}' not found. Check file path!")
        return [] # Return an empty list so the indexer knows it failed
    except Exception as e:
        print(f"🚨 Error reading CSV: {e}")
        return []

if __name__ == '__main__':
    # You would typically use a more robust server like gunicorn for production
    app.run(debug=True, port=5000)
    