**About Project**

Cat Search is a full-stack proof-of-concept application demonstrating a basic search engine pipeline. It integrates a Flask backend with an Elasticsearch service to index and search content. The frontend is a React application that queries the Flask API, which in turn queries Elasticsearch, and combines the results for display.

**Features**

Dual-Source Indexing: Indexes data from a Wikipedia article on cats and posts from the /r/Catmemes subreddit.

Elasticsearch Backend: Uses Elasticsearch for fast, full-text search capabilities.

Flask API: Provides REST endpoints for triggering indexing and performing combined search queries.

Combined Search: Frontend queries both the Wikipedia index and the Reddit meme index simultaneously, displaying results in a unified list with clear source attribution.

**Setup and Installation**

git clone [repository URL]
cd google-search

Backend: </br>
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

Configure Environment Variables: Create a .env file in the root directory and add your Elasticsearch connection details:

# Example for Elastic Cloud:
ELASTIC_HOST_URL=<your-elastic-host.es.us-central1.gcp.cloud.es.io>
ELASTIC_API_KEY=<YOUR_ELASTIC_API_KEY_HERE>

run connect_db.py

Front-end: </br>
rm -rf package-lock.json, node_modules
npm init
npm install
npm run dev to startup the application

