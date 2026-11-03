(() => {
  if (window.__flatComposerBound) return;
  window.__flatComposerBound = true;
  const labelControls = () => {
    for (const prefix of ['ai-console', 'ai-chat']) {
      const send = document.getElementById(`${prefix}-send`);
      send?.setAttribute('aria-label', '发送');
      send?.setAttribute('title', 'Enter 发送，Ctrl+Enter 换行');
      const refresh = document.getElementById(`${prefix}-refresh-models`);
      refresh?.setAttribute('aria-label', '刷新模型');
      refresh?.setAttribute('title', '按需刷新所选后端的模型；Qoder需要先登录');
      document.getElementById(`${prefix}-permission`)?.setAttribute('title', '权限实际传给后端；模型API仅支持只读');
    }
  };
  labelControls();
  new MutationObserver(labelControls).observe(document.body, {childList:true, subtree:true});
  const uploadInput = (composer) => composer?.querySelector('.composer-upload input[type="file"]');
  document.addEventListener('click', (event) => {
    const button = event.target.closest?.('.composer-attach');
    if (!button) return;
    const composer = button.closest('.flat-ai-composer');
    const input = uploadInput(composer);
    if (input) input.click();
    else composer?.querySelector('.composer-upload button')?.click();
  });
  for (const type of ['dragover', 'dragleave', 'drop']) document.addEventListener(type, (event) => {
    const composer = event.target.closest?.('.flat-ai-composer');
    if (!composer || ![...event.dataTransfer?.types || []].includes('Files')) return;
    event.preventDefault();
    composer.classList.toggle('dragging', type === 'dragover');
    if (type !== 'drop' || !event.dataTransfer.files.length) return;
    const input = uploadInput(composer);
    if (!input) return;
    input.files = event.dataTransfer.files;
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });
})();
