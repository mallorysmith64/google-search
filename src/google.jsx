import React from "react";
import googlePic from "./images/google-pic.png";
import { useNavigate } from "react-router-dom";
import Results from "./Results";

function GooglePage() {
  let navigate = useNavigate();
  const handleClick = (event) => {
    event.preventDefault();
    navigate("/results");
  };

  const handleChange = (event) => {
    const newValue = event.target.value;
    console.log(newValue);
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
            />
            <div className="search-btn-container">
              <button
                onClick={handleClick}
                className="search-btn"
              >
                Google Search
              </button>
              <Results />
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
