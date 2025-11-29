import React from "react";
import googlePic from "./images/google-pic.png";

function GooglePage() {

  const handleClick = (event) => {
    const newValue = event.target.value
    console.log(newValue)
  }
  
  return (
    <>
      <div className="google-container">
        <img src={googlePic} alt="Google Logo" />
        <section>
          <form className="form-search" action="/search" method="get">
            <input onClick={handleClick} type="search" name="query" placeholder="Search..." />
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

{/* <input onChange={handleClick} type="search" name="query" placeholder="Search..." /> */}
