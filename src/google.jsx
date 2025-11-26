import React from "react";
import googlePic from "./images/google-pic.png";

function GoogleLogo() {
  return (
    <>
      <div className="google-logo-container">
        <img src={googlePic} alt="Google Logo" />
         <form action="/search" method="get">
        <input type="search" name="query" placeholder="Search..." />
        <button type="submit">Search</button>
      </form>
      </div>
    </>
  );
}

export default GoogleLogo;
