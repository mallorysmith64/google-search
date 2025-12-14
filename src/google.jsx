import React, { useState } from "react";
import googlePic from "./images/google-pic.png";
import catPic from "./images/cat.jpeg";
import { useNavigate } from "react-router-dom";
import Joke from "./Joke.jsx";

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
        <div className="google-container-pics">
          <img src={googlePic} alt="Google Logo" />
          <img className="cat-pic" src={catPic} alt="Cat picture" />
        </div>

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
              <button onClick={handleClick} className="search-btn">
                Google Search
              </button>
            </div>
          </form>
        </section>
        <section className="joke-section">{<Joke />}</section>
      </div>
    </>
  );
}

export default GooglePage;

{
  /* <input onChange={handleClick} type="search" name="query" placeholder="Search..." /> */
}
