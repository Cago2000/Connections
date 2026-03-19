export default function Tile({ word, selected, solved, solvedColor, onClick }) {
    const base = "tile";
    const cls = [base, selected && "selected", solved && "solved"].filter(Boolean).join(" ");
    const style = solved ? { backgroundColor: solvedColor } : {};

    return (
        <button className={cls} style={style} onClick={onClick} disabled={solved}>
            {word}
        </button>
    );
}
