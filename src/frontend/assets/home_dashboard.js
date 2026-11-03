(() => {
  const tooltips = {
    "#home-account-mode": "选择模拟账户或实盘配置视角；实盘缺少 broker 回传时不会伪造资产数据。",
    "#home-refresh": "重新读取账户、行情、新闻和任务快照；会跳过当日缓存。",
    "#home-trend": "净值曲线只使用已保存快照；悬停查看日期和单位净值。",
    "#home-allocation": "查看现金与持仓金额占比；扇区大小代表金额，不代表收益。",
    "#home-risk": "仓位暴露和单票集中度与观察参考线对比；参考线不触发自动交易。",
    "#home-risk-radar": "把仓位、集中度和快照回撤放到同一尺度比较；越靠外表示风险占用越高。",
    "#home-sentiment": "市场情绪代理雷达由指数动量、板块广度和一致性构成，不是买卖信号。",
    "#home-sectors": "板块样本热力图；颜色表示涨跌幅，面积通常表示成交额，缺失时使用等面积。",
    "#home-contribution": "持仓浮动盈亏图；红色为盈利、绿色为亏损，不等同于今日盈亏。",
    "#home-themes": "从当前新闻样本提取的热词与主题，只用于快速了解市场语境。",
    "#home-alerts": "按优先级整理账户、任务和数据异常，先处理高优先级事项。",
    "#home-news": "当前新闻样本；请悬停查看标题和来源，并结合发布时间判断时效。",
    "#home-details": "展开后查看持仓、指数、风格、题材、风险和交易明细。",
  };
  const applyTooltips = () => {
    Object.entries(tooltips).forEach(([selector, text]) => {
      const element = document.querySelector(selector);
      if (!element) return;
      element.setAttribute("title", text);
      element.setAttribute("data-home-tooltip", text);
    });
  };
  applyTooltips();
  new MutationObserver(applyTooltips).observe(document.body, {childList: true, subtree: true});
  document.addEventListener("click", (event) => {
    const link = event.target.closest("[data-home-module]");
    if (!link) return;
    if (window.parent === window) {
      const target = document.querySelector(`#module-navigation [data-module-key="${link.dataset.homeModule}"]`);
      if (target) {
        event.preventDefault();
        location.assign(target.href);
      } else if (link.dataset.homeModule === "ai") {
        const tab = Array.from(document.querySelectorAll('#main-navigation [role="tab"]')).find(el => el.textContent.trim() === "AI工作台");
        if (tab) { event.preventDefault(); tab.click(); }
      }
      return;
    }
    event.preventDefault();
    window.parent.postMessage({type: "aiquant:navigate", module: link.dataset.homeModule}, location.origin);
  });
})();
