import React from "react";
import googlePic from "./images/google-pic.png";

function GooglePage() {
  return (
    <>
      <div className="google-container">
        <img src={googlePic} alt="Google Logo" />
        <section>
          <form className="form-search" action="/search" method="get">
            <input type="search" name="query" placeholder="Search..." />
            <div className="search-btn-container">
              <button className="search-btn" type="submit">
                Google Search
              </button>
              
            </div>
          </form>
        </section>
      </div>
    </>
  );
}

export default GooglePage
