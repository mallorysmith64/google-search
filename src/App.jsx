import GooglePage from "./google";
import NavBar from "./NavBar";
import Footer from "./Footer";
import { BrowserRouter, Routes, Route } from "react-router";
import Results from "./Results";
// import React from 'react'

function App() {
  return (
    <>
      <div>
        <BrowserRouter>
          <NavBar />
         <Routes>
            
            {/* 1. Set the GooglePage as the default route ("/") */}
            <Route path="/" element={<GooglePage />} /> 
            
            {/* 2. The Results page route. Keep this simple, the component handles the search logic */}
            <Route path="/results" element={<Results />} />
            
            {/* 3. Optional: A route for your old search path, redirecting back to the main search page */}
            {/* <Route path="/search" element={<GooglePage />} /> */}
            
          </Routes>
          <Footer />
        </BrowserRouter>
      </div>
    </>
  );
}

export default App;
