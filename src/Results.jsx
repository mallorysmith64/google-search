import React, { useState, useEffect } from "react";
import axios from "axios";
import googlePic from "./images/google-pic.png";

function Results() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);

  const getResults = async () => {
    try {
      const resp = await axios.get(
        "https://www.googleapis.com/customsearch/v1?key=AIzaSyDvknsVPa_byq5U4mjzbHJyeH7TCs1PnpQ&cx=540d53540dba545e2&q=PYTHON"
      );
      console.log("get this query response", resp);
      console.log(resp.data);
      console.log(resp.items);
      console.log("get this query", resp.data.items);
      setResults(resp.data.items || []);
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
    console.log("resp here");
  }, []);

  return (
    <>
      <div className="google-container">
        <img src={googlePic} alt="Google Logo" />

        <section className="search-text-container">
          <div className="results-text-container">
            <h2 className="results-text-header">Results: </h2>
          </div>
          {results.map((item) => (
            <div key={item.url}>
              <h3>{item.title}</h3>
              <p>{item.snippet}</p>
            </div>
          ))}
        </section>
      </div>
    </>
  );
}

export default Results;
