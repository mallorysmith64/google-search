import GooglePage from "./google";
import NavBar from "./NavBar";
import Footer from "./Footer";
import { Routes } from "react-router";
// import Results from "./Results"
// import React from 'react'

function App() {
  return (
    <>
      <div>
        <NavBar />
        <GooglePage />
        {/* <Results/> */}
        <Footer />
       
      </div>
      {/* <Routes>
          {/* Ensure this path matches the URL you are viewing */}
           {/* <Route path="/search" element={<Results/>} />
        </Routes>  */}
    </>
  );
}

export default App;
