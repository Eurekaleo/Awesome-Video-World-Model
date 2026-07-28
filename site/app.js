const state = {
  papers: [],
  filtered: [],
  operation: "all",
  section: "all",
  year: "all",
  sort: "newest",
  query: "",
  visible: 60,
};

const operationLabels = {
  foundations: "Foundations",
  reading: "Reading",
  writing: "Writing",
  sharing: "Sharing",
  interacting: "Interacting",
  frontiers: "Frontiers",
};

const elements = {
  header: document.querySelector("[data-header]"),
  nav: document.querySelector("[data-nav]"),
  navToggle: document.querySelector("[data-nav-toggle]"),
  search: document.querySelector("[data-search]"),
  searchClear: document.querySelector("[data-search-clear]"),
  operationButtons: [...document.querySelectorAll("[data-operation]")],
  operationLinks: [...document.querySelectorAll("[data-operation-link]")],
  section: document.querySelector("[data-section]"),
  year: document.querySelector("[data-year]"),
  sort: document.querySelector("[data-sort]"),
  count: document.querySelector("[data-result-count]"),
  list: document.querySelector("[data-paper-list]"),
  empty: document.querySelector("[data-empty]"),
  loadMore: document.querySelector("[data-load-more]"),
  dialog: document.querySelector("[data-image-dialog]"),
  dialogImage: document.querySelector("[data-dialog-image]"),
  dialogClose: document.querySelector("[data-image-close]"),
};

function refreshIcons(root = document) {
  if (window.lucide) {
    window.lucide.createIcons({
      root,
      attrs: {
        "stroke-width": 1.8,
      },
    });
  }
}

function normalize(value) {
  return value
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function setOperation(operation) {
  state.operation = operation;
  state.section = "all";
  state.visible = 60;
  elements.operationButtons.forEach((button) => {
    const active = button.dataset.operation === operation;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  updateSectionOptions();
  applyFilters();
}

function populateSelect(select, values, allLabel) {
  const previous = select.value;
  select.replaceChildren();
  const all = document.createElement("option");
  all.value = "all";
  all.textContent = allLabel;
  select.append(all);
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = String(value);
    option.textContent = String(value);
    select.append(option);
  });
  select.value = values.map(String).includes(previous) ? previous : "all";
}

function updateSectionOptions() {
  const candidates =
    state.operation === "all"
      ? state.papers
      : state.papers.filter((paper) => paper.operations.includes(state.operation));
  const sections = [...new Set(candidates.map((paper) => paper.primarySection))].sort(
    (a, b) => a.localeCompare(b),
  );
  populateSelect(elements.section, sections, "All sections");
  state.section = elements.section.value;
}

function sortPapers(papers) {
  const sorted = [...papers];
  if (state.sort === "oldest") {
    sorted.sort(
      (a, b) =>
        (a.year || 0) - (b.year || 0) || a.title.localeCompare(b.title),
    );
  } else if (state.sort === "title") {
    sorted.sort((a, b) => a.title.localeCompare(b.title));
  } else {
    sorted.sort(
      (a, b) =>
        (b.year || 0) - (a.year || 0) || a.title.localeCompare(b.title),
    );
  }
  return sorted;
}

function applyFilters() {
  const query = normalize(state.query.trim());
  const tokens = query.split(/\s+/).filter(Boolean);

  state.filtered = sortPapers(
    state.papers.filter((paper) => {
      if (
        state.operation !== "all" &&
        !paper.operations.includes(state.operation)
      ) {
        return false;
      }
      if (
        state.section !== "all" &&
        paper.primarySection !== state.section
      ) {
        return false;
      }
      if (state.year !== "all" && String(paper.year) !== state.year) {
        return false;
      }
      if (tokens.length) {
        const searchable = normalize(
          [
            paper.title,
            paper.authors.join(" "),
            paper.venue,
            paper.venueShort,
            paper.key,
            paper.primarySection,
            paper.operations.join(" "),
          ].join(" "),
        );
        return tokens.every((token) => searchable.includes(token));
      }
      return true;
    }),
  );

  renderPapers();
}

function createIcon(name) {
  const icon = document.createElement("i");
  icon.dataset.lucide = name;
  icon.setAttribute("aria-hidden", "true");
  return icon;
}

function createPaperRow(paper) {
  const row = document.createElement("article");
  row.className = "paper-row";
  row.dataset.operation = paper.operation;

  const main = document.createElement("div");
  main.className = "paper-main";

  const title = document.createElement("a");
  title.className = "paper-title";
  title.href = paper.url;
  title.target = "_blank";
  title.rel = "noopener noreferrer";
  title.textContent = paper.title;
  title.append(" ", createIcon("external-link"));

  const authors = document.createElement("p");
  authors.className = "paper-authors";
  authors.textContent = paper.authorsShort;

  main.append(title, authors);

  const venue = document.createElement("div");
  venue.className = "paper-venue";
  const venueName = document.createElement("strong");
  venueName.textContent = paper.venueShort;
  const year = document.createElement("span");
  year.textContent = paper.year ? String(paper.year) : "Year unavailable";
  venue.append(venueName, year);

  const section = document.createElement("div");
  section.className = "paper-section";
  const sectionName = document.createElement("strong");
  sectionName.textContent = paper.primarySection;
  const operation = document.createElement("span");
  operation.className = "paper-operation";
  operation.textContent = operationLabels[paper.operation] || paper.operation;
  section.append(sectionName, operation);

  row.append(main, venue, section);
  return row;
}

function renderPapers() {
  elements.list.replaceChildren();
  const visible = state.filtered.slice(0, state.visible);
  const fragment = document.createDocumentFragment();
  visible.forEach((paper) => fragment.append(createPaperRow(paper)));
  elements.list.append(fragment);
  elements.list.setAttribute("aria-busy", "false");

  const total = state.filtered.length;
  elements.count.textContent =
    total === state.papers.length
      ? `${total.toLocaleString()} cited papers`
      : `${total.toLocaleString()} matching papers`;

  elements.empty.hidden = total !== 0;
  elements.loadMore.hidden = state.visible >= total || total === 0;
  if (!elements.loadMore.hidden) {
    const remaining = total - state.visible;
    elements.loadMore.firstChild.textContent = `Show more papers (${remaining.toLocaleString()} remaining) `;
  }
  elements.searchClear.hidden = state.query.length === 0;
  refreshIcons(elements.list);
}

async function loadCatalog() {
  try {
    const response = await fetch("data/papers.json");
    if (!response.ok) {
      throw new Error(`Catalog request failed with ${response.status}`);
    }
    const payload = await response.json();
    state.papers = payload.papers;
    const years = [...new Set(state.papers.map((paper) => paper.year).filter(Boolean))].sort(
      (a, b) => b - a,
    );
    populateSelect(elements.year, years, "All years");
    updateSectionOptions();
    applyFilters();
  } catch (error) {
    elements.list.setAttribute("aria-busy", "false");
    elements.count.textContent = "The literature catalog could not be loaded.";
    const message = document.createElement("p");
    message.className = "empty-state";
    message.textContent =
      "Open this page through a web server or visit the repository bibliography.";
    elements.list.append(message);
    console.error(error);
  }
}

function closeNavigation() {
  elements.nav.classList.remove("is-open");
  elements.navToggle.setAttribute("aria-expanded", "false");
  elements.navToggle.setAttribute("aria-label", "Open navigation");
  document.body.classList.remove("is-menu-open");
}

function setupNavigation() {
  elements.navToggle.addEventListener("click", () => {
    const open = !elements.nav.classList.contains("is-open");
    elements.nav.classList.toggle("is-open", open);
    elements.navToggle.setAttribute("aria-expanded", String(open));
    elements.navToggle.setAttribute(
      "aria-label",
      open ? "Close navigation" : "Open navigation",
    );
    document.body.classList.toggle("is-menu-open", open);
  });
  elements.nav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", closeNavigation);
  });
  window.addEventListener("scroll", () => {
    elements.header.classList.toggle("is-scrolled", window.scrollY > 8);
  });
}

function setupFilters() {
  let searchTimer;
  elements.search.addEventListener("input", () => {
    state.query = elements.search.value;
    state.visible = 60;
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(applyFilters, 100);
  });
  elements.searchClear.addEventListener("click", () => {
    elements.search.value = "";
    state.query = "";
    state.visible = 60;
    elements.search.focus();
    applyFilters();
  });
  elements.operationButtons.forEach((button) => {
    button.addEventListener("click", () => setOperation(button.dataset.operation));
  });
  elements.operationLinks.forEach((link) => {
    link.addEventListener("click", () => setOperation(link.dataset.operationLink));
  });
  elements.section.addEventListener("change", () => {
    state.section = elements.section.value;
    state.visible = 60;
    applyFilters();
  });
  elements.year.addEventListener("change", () => {
    state.year = elements.year.value;
    state.visible = 60;
    applyFilters();
  });
  elements.sort.addEventListener("change", () => {
    state.sort = elements.sort.value;
    state.visible = 60;
    applyFilters();
  });
  elements.loadMore.addEventListener("click", () => {
    state.visible += 60;
    renderPapers();
  });
}

function setupFigureDialog() {
  document.querySelectorAll("[data-image-open]").forEach((button) => {
    button.addEventListener("click", () => {
      const image = button.querySelector("img");
      elements.dialogImage.src = button.dataset.imageOpen;
      elements.dialogImage.alt = image ? image.alt : "Enlarged survey figure";
      elements.dialog.showModal();
    });
  });
  elements.dialogClose.addEventListener("click", () => elements.dialog.close());
  elements.dialog.addEventListener("click", (event) => {
    if (event.target === elements.dialog) {
      elements.dialog.close();
    }
  });
}

setupNavigation();
setupFilters();
setupFigureDialog();
loadCatalog();
refreshIcons();
