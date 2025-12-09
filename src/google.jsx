import React, { useState } from "react";
import googlePic from "./images/google-pic.png";
import { useNavigate } from "react-router-dom";

function GooglePage() {
  let navigate = useNavigate();
  const [query, setQuery] = useState("");

  const handleClick = (event) => {
    event.preventDefault();
   navigate("/results", { state: { query: query } });
  };

  const handleChange = (event) => {
    const newValue = event.target.value;
    setQuery(newValue);
  };

  return (
    <>
      <div className="google-container">
        <img src={googlePic} alt="Google Logo" />
        <section>
          <form className="form-search" action="/search" method="get">
            <input
              onChange={handleChange}
              type="search"
              name="query"
              placeholder="Search..."
              value={query}
            />
            <div className="search-btn-container">
              <button
                onClick={handleClick}
                className="search-btn"
              >
                Google Search
              </button>
             
            </div>
          </form>
        </section>
      </div>
    </>
  );
}

export default GooglePage;

{
  /* <input onChange={handleClick} type="search" name="query" placeholder="Search..." /> */
}
