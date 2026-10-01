// 首页中英文切换：默认英文，记忆用户选择到 localStorage。
// 仅作用于首页（带 .language-switch 的页面）。
(function () {
  const STORAGE_KEY = "ai_quant_lang";
  const root = document.documentElement;
  const switcher = document.querySelector(".language-switch");
  if (!switcher) return; // 仅首页执行

  const blocks = {
    en: document.querySelectorAll(".lang-en"),
    zh: document.querySelectorAll(".lang-zh"),
  };

  function setLang(lang) {
    if (!blocks[lang]) return;
    root.setAttribute("data-lang", lang);
    blocks.en.forEach((el) => (el.hidden = lang !== "en"));
    blocks.zh.forEach((el) => (el.hidden = lang !== "zh"));
    switcher.querySelectorAll(".lang-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.lang === lang);
    });
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch (_) {
      /* 隐私模式或无 storage：忽略 */
    }
  }

  switcher.querySelectorAll(".lang-btn").forEach((btn) => {
    btn.addEventListener("click", () => setLang(btn.dataset.lang));
  });

  // 初始化：localStorage > 默认英文
  let initial = "en";
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "zh" || saved === "en") initial = saved;
  } catch (_) {
    /* ignore */
  }
  setLang(initial);
})();