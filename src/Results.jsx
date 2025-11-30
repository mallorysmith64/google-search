import React, { useState, useEffect } from "react";
import axios from "axios";

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
    console.log("use effect is running")
    getResults();
    console.log("resp here");
  }, []);

  return (
    <>
      <div>
        <h2>Results:</h2>
        {/* {results.map((item) => (
          <div key={item.url}>
            <h3>{item.title}</h3>
            <p>{item.snippet}</p>
          </div>
        ))} */}
      </div>
    </>
  );
}

export default Results;
