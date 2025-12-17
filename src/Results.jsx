import React, { useState, useEffect } from "react";
import googlePic from "./images/google-pic.png";
import { useLocation } from "react-router-dom";

function Results() {
  const location = useLocation();
  const query = location.state?.query || "";
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);

  const getResults = async () => {
    if (!query) {
      setLoading(false);
      return;
    }

    setLoading(true);
    const host = "http://127.0.0.1:5000";

    try {
      // STEP 1: Fetch
      const [wikiRes, redditRes, cfaRes] = await Promise.all([
        fetch(`${host}/search?q=${query}`).catch(() => ({ json: () => ({ results: [] }) })),
        fetch(`${host}/search_reddit?q=${query}`).catch(() => ({ json: () => ({ results: [] }) })),
        fetch(`${host}/search_cfa?q=${query}`).catch(() => ({ json: () => [] }))
      ]);

      // STEP 2: Parse
      const wikiData = await wikiRes.json();
      const redditData = await redditRes.json();
      const cfaData = await cfaRes.json();

      // STEP 3: Normalize (Everything happens INSIDE here now)
      const normalizedWiki = (wikiData.results || []).map(item => ({
        ...item,
        source_type: "Wikipedia Article"
      }));

      const normalizedReddit = redditData.results || [];

      const normalizedCfa = (Array.isArray(cfaData) ? cfaData : []).map(item => ({
        title: item.name || "Unknown Breed",
        snippet: item.description || "No description available",
        url: item.url,
        source_type: "CFA Breed Profile"
      }));

      // STEP 4: Set results
      setResults([...normalizedCfa, ...normalizedReddit, ...normalizedWiki]);

    } catch (error) {
      console.error("Search failed:", error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  // --- DELETE THE ORPHANED cfaResults BLOCK THAT WAS HERE ---

  useEffect(() => {
    getResults();
  }, [query]);

  if (loading) {
    return <div className="loading-container">Loading cat data...</div>;
  }

  return (
    <div className="google-container">
      <img src={googlePic} alt="Google Logo" style={{ width: '150px' }} />

      <section className="search-text-container">
        <div className="results-text-container">
          <h2 className="results-text-header">
            {query ? `Results for: "${query}" (${results.length} total)` : "Please enter a search query."}
          </h2>
        </div>

        {results.length > 0 ? (
          results.map((item, index) => (
            <div key={item.url || index} className="result-item">
              <a href={item.url} target="_blank" rel="noopener noreferrer">
                <h3>
                  {item.title}
                  <span style={{ 
                    fontSize: '0.7em', 
                    marginLeft: '10px',
                    color: item.source_type === 'Reddit Meme' ? 'red' : 
                           item.source_type === 'CFA Breed Profile' ? '#0056b3' : 'green' 
                  }}>
                    [{item.source_type}]
                  </span>
                </h3>
              </a>
              <p className="result-url">{item.url}</p>
              <p className="result-snippet">{item.snippet}</p>
            </div>
          ))
        ) : (
          <p>No results found for your search.</p>
        )}
      </section>
    </div>
  );
}

export default Results;