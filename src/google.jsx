import React from "react";
import googlePic from "./images/google-pic.png";

function GoogleLogo() {
  return (
    <>
      <div className="google-container">
        <img src={googlePic} alt="Google Logo" />
        <section className="search-bar-container">
          <form action="/search" method="get">
            <input type="search" name="query" placeholder="Search..." />
            <button type="submit">Search</button>
          </form>
        </section>
      </div>
    </>
  );
}

export default GoogleLogo;
