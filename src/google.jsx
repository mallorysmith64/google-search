import React from "react";
import googlePic from "./images/google-pic.png";
import { useNavigate } from "react-router-dom";
import Results from "./Results";

function GooglePage() {
  let navigate = useNavigate();
  const handleNavigate = () => {
    navigate("/results"); // Navigates to /some-path
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
                onClick={handleNavigate}
                className="search-btn"
                type="submit"
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
