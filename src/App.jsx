import GooglePage from "./google";
import NavBar from "./NavBar";
import Footer from "./Footer";
// import SearchResultsPage from "./Results";

function App() {
  return (
    <>
      <div>
        <NavBar />
        <GooglePage />
        {/* <SearchResultsPage /> */}
        <Footer />
      </div>
    </>
  );
}

export default App;
