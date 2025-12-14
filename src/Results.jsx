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
    const host = "http://127.0.0.1:5000"; // Define host for easy maintenance

    try {
      // 1. Define both fetch operations using Promise.all
      const [wikiResponse, redditResponse] = await Promise.all([
        // Fetch 1: Wikipedia Search
        fetch(`${host}/search?q=${query}`).catch(err => {
            console.error("Wikipedia search failed:", err);
            return { json: () => ({ results: [] }) }; // Return fallback for failed promise
        }),
        // Fetch 2: Reddit Search
        fetch(`${host}/search_reddit?q=${query}`).catch(err => {
            console.error("Reddit search failed:", err);
            return { json: () => ({ results: [] }) }; // Return fallback for failed promise
        })
      ]);

      // 2. Parse JSON from both responses
      const wikiData = await wikiResponse.json();
      const redditData = await redditResponse.json();
      
      // 3. Normalize and combine the data
      
      // Normalize Wikipedia results (add source type)
      const wikiResults = (wikiData.results || []).map(item => ({
        ...item,
        source_type: "Wikipedia Article"
      }));

      // Reddit results already have source_type, just handle the fallback
      const redditResults = redditData.results || [];

      // Combine Reddit results (memes) first, then Wikipedia articles
      const combinedResults = [...redditResults, ...wikiResults];
      
      // console.log("Combined Results:", combinedResults); // Uncomment for debugging
      setResults(combinedResults);

    } catch (error) {
      console.error("Error fetching search results:", error);
      setResults([]);
    } finally {
      setLoading(false); // Stop loading regardless of success/failure
    }
  };

  useEffect(() => {
    console.log("use effect is running");
    getResults();
  }, [query]);

  if (loading) {
    return <div>Loading results...</div>;
  }

  const headerText = query
    ? `Results for: "${query}" (${results.length} total)`
    : "Please enter a search query.";

  return (
    <>
      <div className="google-container">
        <img src={googlePic} alt="Google Logo" />

        <section className="search-text-container">
          <div className="results-text-container">
            <h2 className="results-text-header">{headerText} </h2>
          </div>
          {results.length > 0 ? (
            results.map((item, index) => (
              // Use index or a combination of url/title/source_type as a key, since item.id might be duplicated
              <div key={item.url || index} className="result-item">
                <a href={item.url} target="_blank" rel="noopener noreferrer">
                  <h3>
                    {item.title || 'No Title'}
                    {/* Display Source Type */}
                    <span style={{ fontSize: '0.8em', color: item.source_type === 'Reddit Meme' ? 'red' : 'green', marginLeft: '10px' }}>
                        [{item.source_type}]
                    </span>
                  </h3>
                </a>
                <p className="result-url">{item.url}</p>
                <p className="result-snippet">{item.snippet}</p>
                {/* Optional: Display score for debugging relevance */}
                <p>Score: {item.score}</p>
              </div>
            ))
          ) : (
            <div>
              <p>No results found.</p>
            </div>
          )}
        </section>
      </div>
    </>
  );
}

export default Results;