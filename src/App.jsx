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
          
          <Routes>
            {/* 1. Root Route: Only googlepage has navbar and footer on "/" */}
            <Route
              path="/"
              element={
                <>
                  <NavBar /> {/* The NavBar is included here */}
                  <GooglePage />
                  <Footer/>
                </>
              }
            />

            {/* 2. The Results page route. Keep this simple, the component handles the search logic */}
            <Route path="/results" element={<Results />} />

            {/* 3. Optional: A route for your old search path, redirecting back to the main search page */}
            {/* <Route path="/search" element={<GooglePage />} /> */}
          </Routes>
         
        </BrowserRouter>
      </div>
    </>
  );
}

export default App;
