/* Reuse the MkDocs index while supporting Chinese substrings and English terms. */
(() => {
  const root = new URL("../../", document.currentScript.src);
  let indexPromise;

  function loadIndex() {
    if (!indexPromise) {
      indexPromise = fetch(new URL("search/search_index.json", root))
        .then((response) => {
          if (!response.ok) throw new Error(response.statusText);
          return response.json();
        })
        .catch((error) => {
          indexPromise = undefined;
          throw error;
        });
    }
    return indexPromise;
  }

  function resultElement(entry) {
    const article = document.createElement("article");
    const heading = document.createElement("h3");
    const link = document.createElement("a");
    link.href = new URL(entry.location, root).href;
    link.textContent = entry.title;
    heading.append(link);
    const excerpt = document.createElement("p");
    excerpt.textContent = entry.text;
    article.append(heading, excerpt);
    return article;
  }

  document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("mkdocs-search-query");
    const results = document.getElementById("mkdocs-search-results");
    if (!input || !results) return;
    results.setAttribute("aria-live", "polite");
    let revision = 0;

    async function search() {
      const current = ++revision;
      const query = input.value.trim().toLowerCase();
      results.replaceChildren();
      if (!query) return;
      try {
        const index = await loadIndex();
        if (current !== revision || query.length < index.config.min_search_length) return;
        const terms = query.split(/\s+/);
        const candidates = index.docs.filter((entry) => {
          if (!/^(usage|principles)\//.test(entry.location)) return false;
          const text = (entry.title + " " + entry.text).toLowerCase();
          return terms.every((term) => text.includes(term));
        });
        const pages = new Map();
        const score = (entry) => Number(entry.title.toLowerCase().includes(query));
        for (const entry of candidates) {
          const key = entry.location.split("#")[0];
          if (!pages.has(key) || score(entry) > score(pages.get(key))) pages.set(key, entry);
        }
        const matches = Array.from(pages.values()).sort((left, right) => score(right) - score(left));
        results.replaceChildren(...matches.map(resultElement));
        if (!matches.length) results.textContent = results.dataset.noResultsText || "";
      } catch (error) {
        if (current === revision) results.textContent = String(error);
      }
    }

    input.addEventListener("input", search);
    input.closest("form")?.addEventListener("submit", (event) => event.preventDefault());
    const query = new URLSearchParams(location.search).get("q");
    if (query) {
      input.value = query;
      search();
    }
  });
})();
