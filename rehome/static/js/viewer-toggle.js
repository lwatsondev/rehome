const toggle = document.getElementById("viewer-toggle");
const rendered = document.getElementById("viewer-rendered");
const source = document.getElementById("viewer-source");
const codeEl = source.querySelector("code");
let loadPromise = null;

toggle.addEventListener("click", async (e) => {
    e.preventDefault();

    if (source.hidden) {
        loadPromise ??= fetch(toggle.href)
            .then((r) => r.text())
            .then((text) => {
                codeEl.textContent = text;
                delete codeEl.dataset.highlighted;
                highlightWithLineNumbers(codeEl);
            });
        await loadPromise;
    }

    const showSource = source.hidden;
    rendered.hidden = showSource;
    source.hidden = !showSource;
    toggle.textContent = showSource ? "rendered" : "source";
});
