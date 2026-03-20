import { useEffect, useState } from "react";
import Board from "./Board";
import { initDiscord } from "./sdk";

const MAX_SELECTED = 4;
const today = new Date().toISOString().split("T")[0];

export default function App() {
    const [user, setUser] = useState(null);
    const [puzzle, setPuzzle] = useState(null);
    const [player, setPlayer] = useState(null);
    const [selected, setSelected] = useState([]);
    const [message, setMessage] = useState("");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function init() {
            const userData = await initDiscord();
            setUser(userData);

            const [puzzleRes, stateRes] = await Promise.all([
                fetch(`/api/puzzle/${today}`),
                fetch(`/api/state/${today}/${userData.user_id}`),
            ]);

            const puzzleData = puzzleRes.ok ? await puzzleRes.json() : null;
            if (puzzleData) puzzleData.words = shuffleArray(puzzleData.words);
            const playerData = stateRes.ok ? await stateRes.json() : null;

            setPuzzle(puzzleData);
            setPlayer(playerData);
            setLoading(false);
        }
        init();
    }, []);

    function toggleTile(word) {
        if (selected.includes(word)) {
            setSelected(selected.filter(w => w !== word));
            return;
        }
        if (selected.length >= MAX_SELECTED) return;
        setSelected([...selected, word]);
    }

    function shuffleArray(arr) {
        const a = [...arr];
        for (let i = a.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [a[i], a[j]] = [a[j], a[i]];
        }
        return a;
    }

    function shuffle() {
        setPuzzle(p => ({ ...p, words: [...p.words].sort(() => Math.random() - 0.5) }));
    }

    async function submitGuess() {
        if (selected.length !== MAX_SELECTED) return;

        const res = await fetch("/api/guess", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: user.user_id, date: today, selected }),
        });

        const result = await res.json();
        setSelected([]);
        setPlayer(result.player);

        if (result.correct) {
            setMessage(`✅ ${result.group}!`);
        } else if (result.one_away) {
            setMessage("One away...");
        } else {
            setMessage("Not quite!");
        }

        setTimeout(() => setMessage(""), 2000);
    }

    async function shareResult() {
        const res = await fetch(`/api/share/${today}/${user.user_id}`);
        const { text } = await res.json();
        await navigator.clipboard.writeText(text);
        setMessage("Copied to clipboard!");
        setTimeout(() => setMessage(""), 2000);
    }

    if (loading) return <div className="screen-center">Loading...</div>;
    if (!puzzle) return <div className="screen-center">No puzzle today.</div>;
    if (!player) return <div className="screen-center">Loading...</div>;

    const mistakesLeft = 4 - player.mistakes;
    const solvedGroups = puzzle.groups
        .filter(g => player.solved_groups.includes(g.level))
        .map(g => ({ ...g, members: puzzle.words.filter(w => false) }));

    return (
        <div className="app">
            <h1 className="title">Connections</h1>
            <p className="subtitle">Create four groups of four!</p>

            <Board
                words={puzzle.words}
                selected={selected}
                solvedGroups={solvedGroups}
                onTileClick={toggleTile}
            />

            {message && <div className="message">{message}</div>}

            <div className="mistakes">
                Mistakes remaining: {"●".repeat(mistakesLeft)}{"○".repeat(4 - mistakesLeft)}
            </div>

            <div className="controls">
                <button className="btn-secondary" onClick={() => setSelected([])}>Deselect All</button>
                <button className="btn-secondary" onClick={shuffle}>Shuffle</button>
                <button
                    className="btn-primary"
                    onClick={submitGuess}
                    disabled={selected.length !== MAX_SELECTED || player.completed}
                >
                    Submit
                </button>
            </div>

            {player.completed && (
                <button className="btn-share" onClick={shareResult}>Share Result</button>
            )}
        </div>
    );
}