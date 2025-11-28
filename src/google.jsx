import React from "react";
import googlePic from "./images/google-pic.png";

function GoogleLogo() {
  return (
    <>
      <div className="google-container">
        <img src={googlePic} alt="Google Logo" />
        <section>
          <form className="form-search" action="/search" method="get">
           <div class="gcse-search"></div>
            <script
                async
                src="https://cse.google.com/cse.js?cx=540d53540dba545e2"
              ></script>
             
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

export default GoogleLogo;
