import React, { useState, useEffect } from "react";

function Joke() {
    const [joke, setJoke] = useState({ setup: "", punchline: "" });

    useEffect(() => {
        let cancelled = false;

        async function loadJoke() {
            try {
                const resp = await fetch("https://official-joke-api.appspot.com/random_joke");
                console.log(resp);
                if (!resp.ok) throw new Error(resp.statusText);
                const data = await resp.json();
                if (!cancelled) setJoke(data);
            } catch (err) {
                console.error("Failed to load joke:", err);
            }
        }

        loadJoke();
        return () => {
            cancelled = true;
        };
    }, []);

    return (
        <>
            <h1>Joke of the Day:</h1>
            <p>{joke.setup}</p>
            <p><strong>{joke.punchline}</strong></p>
        </>
    );
}
export default Joke