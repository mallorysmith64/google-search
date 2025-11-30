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
          <GooglePage />
          <Routes>
            <Route path="/search?query=" element={<GooglePage/>}/>
            <Route path="/results" element={<Results />} />
          </Routes>
          <Footer />
        </BrowserRouter>
      </div>
    </>
  );
}

export default App;
