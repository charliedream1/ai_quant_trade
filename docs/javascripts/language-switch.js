// 全站中英文切换器
// ---------------------------------------------------------------------------
// 设计：
// - 默认英文，记忆用户选择到 localStorage（key: "ai_quant_lang"）。
// - 正文部分：首页沿用 .lang-en / .lang-zh 双块；切换时改 hidden 属性。
//   其他页不需要切（内容是单语中文）。
// - 顶部标签页（tabs）和左侧导航（sidebar）：mkdocs-material 把 nav
//   渲染为 .md-tabs__link / .md-nav__link 等元素。MkDocs 不会从 yaml
//   自动生成 data-i18n 属性，所以这里按实际文本做稳定映射。
// - 切换按钮：本脚本会创建一个浮动的 .language-switch 控件（如果页面已
//   有 .language-switch 容器，则填进去），默认右下方悬浮显示。
// ---------------------------------------------------------------------------

(function () {
  const STORAGE_KEY = "ai_quant_lang";
  let currentLang = "en";
  let materialHookBound = false;
  const SITE_LABELS = [
    ["AI量化交易操盘手", "AI Quant Trader"],
  ];
  const NAV_LABELS = [
    ["首页", "Home"],
    ["环境配置", "Environment"],
    ["GPU 环境配置", "GPU Environment"],
    ["GPU 配置 (Windows)", "GPU Setup (Windows)"],
    ["Python 环境配置", "Python Environment"],
    ["Conda 安装", "Conda Install"],
    ["Conda 国内源配置", "Conda Mirrors"],
    ["Miniconda 安装", "Miniconda Install"],
    ["常见问题", "FAQ"],
    ["Python 包依赖问题", "Python Dependencies"],
    ["GitHub 问题", "GitHub Issues"],
    ["numpy 版本问题", "numpy Version Issues"],
    ["星球使用", "Community"],
    ["星球介绍", "Community Overview"],
    ["新人使用指南", "New User Guide"],
    ["部署运维", "Deployment"],
    ["发布操作指南", "Publishing Guide"],
    ["Cloudflare Pages 部署", "Cloudflare Pages"],
  ];

  const SITE_TO_EN = new Map(SITE_LABELS);
  const SITE_TO_ZH = new Map(SITE_LABELS.map(([zh, en]) => [en, zh]));
  const NAV_TO_EN = new Map(NAV_LABELS);
  const NAV_TO_ZH = new Map(NAV_LABELS.map(([zh, en]) => [en, zh]));

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

  function normalizeText(text) {
    return text.replace(/\s+/g, " ").trim();
  }

  function translateLabel(text, lang) {
    const label = normalizeText(text);
    if (!label) return null;
    return lang === "en" ? NAV_TO_EN.get(label) : NAV_TO_ZH.get(label);
  }

  function translateSiteLabel(text, lang) {
    const label = normalizeText(text);
    if (!label) return null;
    return lang === "en" ? SITE_TO_EN.get(label) : SITE_TO_ZH.get(label);
  }

  function getNavTextTarget(el) {
    return el.querySelector(".md-ellipsis") || el;
  }

  // Apply translations to nav (top tabs + sidebar).
  function applyNavLang(lang) {
    document.querySelectorAll(".md-tabs__link, .md-nav__link").forEach((el) => {
      const target = getNavTextTarget(el);
      const translated = translateLabel(target.textContent, lang);
      if (translated == null) return;
      target.textContent = translated;
      target.setAttribute("data-i18n-active", lang);
    });

    document.querySelectorAll(".md-breadcrumb__link").forEach((el) => {
      const translated = translateLabel(el.textContent, lang);
      if (translated == null) return;
      el.textContent = translated;
      el.setAttribute("data-i18n-active", lang);
    });
  }

  function applySiteChromeLang(lang) {
    document
      .querySelectorAll(".md-header__title .md-ellipsis, .md-nav__title")
      .forEach((el) => {
        const translated = translateSiteLabel(el.textContent, lang);
        if (translated == null) return;
        el.textContent = translated;
        el.setAttribute("data-i18n-active", lang);
      });

    document.querySelectorAll("[data-md-component='logo']").forEach((el) => {
      ["aria-label", "title"].forEach((attr) => {
        const value = el.getAttribute(attr);
        const translated = value == null ? null : translateSiteLabel(value, lang);
        if (translated != null) {
          el.setAttribute(attr, translated);
        }
      });
    });

    const title = translateSiteLabel(document.title, lang);
    if (title != null) {
      document.title = title;
    }
  }

  function waitForNavAndApply(lang) {
    applyNavLang(lang);
    applySiteChromeLang(lang);
    let attempts = 0;
    const timer = window.setInterval(() => {
      attempts += 1;
      applyNavLang(lang);
      applySiteChromeLang(lang);
      if (attempts >= 20) {
        window.clearInterval(timer);
      }
    }, 100);

    if (
      !materialHookBound &&
      window.document$ &&
      typeof window.document$.subscribe === "function"
    ) {
      materialHookBound = true;
      window.document$.subscribe(() => {
        applyContentLang(currentLang);
        applyNavLang(currentLang);
        applySiteChromeLang(currentLang);
      });
    }
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
    currentLang = lang;
    applyContentLang(lang);
    waitForNavAndApply(lang);
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
