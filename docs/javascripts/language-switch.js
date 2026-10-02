// 全站中英文切换器
// ---------------------------------------------------------------------------
// 设计：
// - 默认英文，记忆用户选择到 localStorage（key: "ai_quant_lang"）。
// - 正文部分：首页沿用 .lang-en / .lang-zh 双块；切换时改 hidden 属性。
//   其他页不需要切（内容是单语中文）。
// - 顶部标签页（tabs）和左侧导航（sidebar）：mkdocs-material 把 nav
//   渲染为 .md-tabs__link / .md-nav__link 等元素。我们给 nav 配置项打
//   data-i18n-en / data-i18n-zh 属性（位于导航的 a 标签或父级 li 上），
//   切换时改 textContent。
// - 切换按钮：本脚本会创建一个浮动的 .language-switch 控件（如果页面已
//   有 .language-switch 容器，则填进去），默认右下方悬浮显示。
// ---------------------------------------------------------------------------

(function () {
  const STORAGE_KEY = "ai_quant_lang";

  // Read current language preference.
  function getSavedLang() {
    try {
      const v = localStorage.getItem(STORAGE_KEY);
      return v === "zh" || v === "en" ? v : "en";
    } catch (_) {
      return "en";
    }
  }

  function saveLang(lang) {
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch (_) {
      /* ignore */
    }
  }

  // Apply translations to nav (top tabs + sidebar).
  // We rely on data-i18n-en / data-i18n-zh on the anchor or its parent <li>.
  function applyNavLang(lang) {
    const other = lang === "en" ? "zh" : "en";
    document
      .querySelectorAll("[data-i18n-en], [data-i18n-zh]")
      .forEach((el) => {
        const text = el.getAttribute("data-i18n-" + lang);
        if (text == null) return;
        el.textContent = text;
        // Hint which language is currently "hidden" (for future-proofing).
        el.setAttribute("data-i18n-active", lang);
      });
    // Suppress unused warning by referencing `other` via noop.
    void other;
  }

  // Apply language to body content (homepage .lang-en / .lang-zh blocks).
  function applyContentLang(lang) {
    document.querySelectorAll(".lang-en").forEach((el) => {
      el.hidden = lang !== "en";
    });
    document.querySelectorAll(".lang-zh").forEach((el) => {
      el.hidden = lang !== "zh";
    });
    document.documentElement.setAttribute("data-lang", lang);
  }

  // Build the floating switcher button (English / 中文). If the page already
  // provides a .language-switch container (e.g. the homepage), we wire up
  // buttons inside it instead of creating the floating one.
  function buildSwitcher(onChange) {
    const existing = document.querySelector(".language-switch");
    if (existing) {
      existing.querySelectorAll(".lang-btn").forEach((btn) => {
        btn.addEventListener("click", () => onChange(btn.dataset.lang));
      });
      return existing;
    }

    // Floating fallback (visible on every non-homepage page).
    const wrap = document.createElement("div");
    wrap.className = "language-switch language-switch--floating";
    wrap.setAttribute("aria-label", "Language switcher");
    wrap.innerHTML =
      '<button class="lang-btn" data-lang="en" type="button" aria-pressed="true">EN</button>' +
      '<button class="lang-btn" data-lang="zh" type="button" aria-pressed="false">中</button>';
    document.body.appendChild(wrap);
    wrap.querySelectorAll(".lang-btn").forEach((btn) => {
      btn.addEventListener("click", () => onChange(btn.dataset.lang));
    });
    return wrap;
  }

  function setSwitcherActive(switcher, lang) {
    if (!switcher) return;
    switcher.querySelectorAll(".lang-btn").forEach((btn) => {
      const active = btn.dataset.lang === lang;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function setLang(lang, switcher) {
    applyContentLang(lang);
    applyNavLang(lang);
    setSwitcherActive(switcher, lang);
    saveLang(lang);
  }

  function init() {
    const switcher = buildSwitcher((lang) => setLang(lang, switcher));
    const initial = getSavedLang();
    setLang(initial, switcher);
  }

  // mkdocs-material initializes navigation asynchronously; we wait for DOM
  // ready, then for first paint of nav, then apply.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
