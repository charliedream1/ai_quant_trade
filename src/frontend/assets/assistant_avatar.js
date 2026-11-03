(() => {
  if(window.__assistantAvatarReady)return;window.__assistantAvatarReady=true;
  let cfg,style=localStorage.getItem('aiquant-assistant-style');
  const apply=()=>{const button=document.getElementById('ai-floating-button');if(!button||!cfg)return;
    const image=cfg.avatar.images[style]||cfg.avatar.images[cfg.avatar.style];
    button.style.setProperty('--assistant-image',`url("${image}")`);button.classList.add('assistant-avatar');
    button.setAttribute('aria-label',cfg.ui.assistant);button.setAttribute('title',cfg.ui.assistant);
  };
  fetch('__NOTICE_CONFIG__').then(response=>response.json()).then(body=>{cfg=body.data;apply();}).catch(()=>{});
  window.addEventListener('message',event=>{if(event.origin===location.origin&&event.source===parent&&event.data?.type==='aiquant:assistant-style'){style=event.data.style;localStorage.setItem('aiquant-assistant-style',style);apply();}});
  new MutationObserver(apply).observe(document.body,{childList:true,subtree:true});
})();
