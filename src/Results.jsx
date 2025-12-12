import React, { useState, useEffect } from "react";
import googlePic from "./images/google-pic.png";
import { useLocation } from "react-router-dom";

function Results() {
  const location = useLocation();
  const query = location.state?.query || "";
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);

  const getResults = async () => {
    try {
      const resp = await fetch(
        `http://127.0.0.1:5000/search?q=${query}`
      );
      const data = await resp.json()
      console.log("get this query response", resp);
     setResults(data.results || []);
    } catch (error) {
      console.error("Error fetching search results:", error);
      setResults([]);
    } finally {
      setLoading(false); // Stop loading
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
    ? `Results for: "${query}"`
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
            results.map((item) => (
              // Use item.url as key, as it's likely unique from your CSV
              <div key={item.id} className="result-item">
                <a href={item.url} target="_blank" rel="noopener noreferrer">
                  <h3>{item.title}</h3>
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
