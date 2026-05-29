function addLineNumbers(codeEl) {
    codeEl.querySelectorAll("tr").forEach((row, i) => {
        row.id = `L${i + 1}`;
        const numCell = row.querySelector(".hljs-ln-numbers");
        if (numCell) numCell.textContent = i + 1;
    });

    codeEl.closest("pre")?.classList.add("viewer-pre-lined");
}

function highlightWithLineNumbers(block) {
    hljs.highlightElement(block);
    block.innerHTML = hljs.lineNumbersValue(block.innerHTML);
    addLineNumbers(block);
}

document.querySelectorAll("pre.viewer-pre code").forEach((block) => {
    if (!block.textContent.trim()) return;
    highlightWithLineNumbers(block);
});

hljs.highlightAll();
