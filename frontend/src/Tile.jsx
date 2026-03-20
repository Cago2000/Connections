function fontSize(word, max = 12) {
    const vw = document.body.offsetWidth;
    const tileSize = (vw - 16 - 18) / 4;
    return `${Math.min(max, Math.floor((tileSize * 1.0) / word.length))}px`;
}

export default function Tile({ word, selected, solved, solvedColor, onClick }) {
    const cls = ["tile", selected && "selected", solved && "solved"].filter(Boolean).join(" ");
    const style = {
        ...(solved ? { backgroundColor: solvedColor } : {}),
        fontSize: fontSize(word),
    };

    return (
        <button type="button" className={cls} style={style} onClick={onClick} disabled={solved}>
            {word}
        </button>
    );
}