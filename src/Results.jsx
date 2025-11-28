import React, { useState, useEffect} from 'React'
// import axios from 'axios'

function SearchResultsPage() {
    const [results, setResults] = useState([]);
    const getResults = async () => {
    const resp = await axios.get('https://www.googleapis.com/customsearch/v1?key=AIzaSyDvknsVPa_byq5U4mjzbHJyeH7TCs1PnpQ&cx=540d53540dba545e2&q=PYTHON')
    console.log('get this query response', resp)
    console.log('get this query', resp.data)
    set(resp.data)
  }

  useEffect(() => {
    getResults
  }, [])

    return (
        <>
        <div>
          <h2>Results:</h2>
          {results.map(item => (
            <div key={item.url}>
              <h3>{item.title}</h3>
              <p>{item.snippet}</p>
            </div>
          ))}
        </div>
        </>
    )
}

export default SearchResultsPage