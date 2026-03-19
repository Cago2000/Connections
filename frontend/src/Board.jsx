import Tile from "./Tile";

const LEVEL_COLORS = {
    0: "#f9df6d", // yellow
    1: "#a0c35a", // green
    2: "#b0c4ef", // blue
    3: "#ba81c5", // purple
};

export default function Board({ words, selected, solvedGroups, onTileClick }) {
    const solvedWords = new Set(solvedGroups.flatMap(g => g.members));

    const solvedColorMap = {};
    for (const g of solvedGroups) {
        for (const w of g.members) {
            solvedColorMap[w] = LEVEL_COLORS[g.level];
        }
    }

    return (
        <div className="board">
            {solvedGroups.map(g => (
                <div key={g.level} className="solved-row" style={{ backgroundColor: LEVEL_COLORS[g.level] }}>
                    <span className="solved-group-name">{g.group}</span>
                    <span className="solved-members">{g.members.join(", ")}</span>
                </div>
            ))}

            <div className="tile-grid">
                {words.filter(w => !solvedWords.has(w)).map(word => (
                    <Tile
                        key={word}
                        word={word}
                        selected={selected.includes(word)}
                        solved={false}
                        onClick={() => onTileClick(word)}
                    />
                ))}
            </div>
        </div>
    );
}
