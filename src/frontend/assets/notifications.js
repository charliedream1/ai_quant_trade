() => {
  const start = async () => {
    const bell = document.getElementById('workspace-notification-toggle');
    if (!bell || bell.dataset.ready) return Boolean(bell);
    bell.dataset.ready = '1';
    let cfg;
    try { cfg = (await (await fetch(bell.dataset.configUrl)).json()).data; }
    catch (_) { bell.dataset.ready = ''; bell.title=bell.dataset.offline;setTimeout(start,Number(bell.dataset.retrySeconds)*1000);return true; }
    window.__aiquantNotificationConfig = cfg;
    const ui = cfg.ui;
    const node = (tag, text, cls) => { const el = document.createElement(tag); if (text) el.textContent = text; if (cls) el.className = cls; return el; };
    const box = node('aside', '', 'notification-center'); box.id = 'notification-center'; box.hidden = true;
    box.setAttribute('aria-label', ui.title);
    const header = node('header'); header.append(node('strong', ui.title));
    const close = node('button', '×'); close.setAttribute('aria-label', ui.close); close.onclick = () => {box.hidden = true; bell.setAttribute('aria-expanded','false'); bell.focus();}; header.append(close);
    const toolbar = node('div', '', 'notification-toolbar');
    const allRead = node('button', ui.read_all); toolbar.append(allRead);
    const note = node('p', '', 'notification-status'); note.setAttribute('role', 'status');
    const entries = node('div', '', 'notification-entries');
    const more = node('button', ui.more); more.hidden = true;
    const footer = node('footer'); const label = node('label', ui.appearance); const style = node('select');
    style.setAttribute('aria-label', ui.appearance);
    Object.keys(cfg.avatar.images).forEach(key => {const opt=node('option',ui[key]); opt.value=key; style.append(opt);});
    const selectedStyle=localStorage.getItem('aiquant-assistant-style');
    style.value = Object.hasOwn(cfg.avatar.images,selectedStyle)?selectedStyle:cfg.avatar.style;
    label.append(style); footer.append(label); box.append(header,toolbar,note,entries,more,footer); document.body.append(box);
    const toasts = node('section', '', 'notification-toasts'); toasts.id='notification-toasts'; toasts.setAttribute('aria-label',ui.title); document.body.append(toasts);
    const banner = node('button', '', 'notification-critical'); banner.id='notification-critical'; banner.hidden=true; document.body.append(banner);
    toasts.style.width=`min(${cfg.toast_width}px,calc(100vw - 24px))`;
    const position=()=>{const top=Math.ceil(document.querySelector('.workspace-topbar').getBoundingClientRect().bottom)+8;box.style.top=top+'px';banner.style.top=top+'px';toasts.style.top=(top+(banner.hidden?0:banner.offsetHeight+10))+'px';};
    new ResizeObserver(position).observe(document.querySelector('.workspace-topbar'));window.addEventListener('resize',position);
    const open = () => {box.hidden=false;bell.setAttribute('aria-expanded','true');close.focus();};
    bell.setAttribute('title',ui.open); bell.setAttribute('aria-label',ui.open); bell.setAttribute('aria-expanded','false');
    bell.onclick=()=>box.hidden?open():close.click(); banner.onclick=open;
    document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!box.hidden)close.click();});
    style.onchange=()=>{localStorage.setItem('aiquant-assistant-style',style.value);document.querySelectorAll('iframe.workspace-frame').forEach(frame=>frame.contentWindow.postMessage({type:'aiquant:assistant-style',style:style.value},location.origin));};
    let client=localStorage.getItem('aiquant-notification-client');
    if(!client){client=crypto.randomUUID();localStorage.setItem('aiquant-notification-client',client);}
    const cursorKey='aiquant-notification-cursor:'+client;
    let cursor=Number(localStorage.getItem(cursorKey)||0),initial=!localStorage.getItem(cursorKey),busy=false,again=false,timer,older=0,items=[];
    const seen=new Set(),visible=new Map();
    const request=async(path, options)=>{const response=await fetch(cfg.api+path,options);const body=await response.json();if(!response.ok||body.code!==0)throw Error('notification unavailable');return body.data;};
    const action=async(id,kind)=>request('/'+id+'/state',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({client_id:client,action:kind})});
    const navigate=async(row)=>{try{await action(row.id,'read');}catch(_){} window.dispatchEvent(new CustomEvent('aiquant:notification-open',{detail:row.target}));close.click();refresh();};
    const card=(row,toast=false)=>{
      const article=node('article','', 'notification-card '+row.severity);article.dataset.notificationId=String(row.id);
      const top=node('div','', 'notification-card-top');top.append(node('span',ui[row.severity],'notification-severity'),node('strong',row.title));
      const dismiss=node('button','×');dismiss.setAttribute('aria-label',ui.close+' '+row.title);
      dismiss.onclick=async()=>{try{await action(row.id,'dismiss');row.dismissed_at=true;items=items.map(item=>item.id===row.id?{...item,dismissed_at:true}:item);removeToast(row.id);render();}catch(_){note.textContent=ui.offline;}};top.append(dismiss);
      const description=node('p',row.message); const time=node('small',new Date(row.occurred_at).toLocaleString()+' '+(row.resolved_at?ui.resolved:row.read_at?'':ui.unread)+' '+(row.dismissed_at?ui.dismissed:''));
      const actions=node('div','', 'notification-card-actions');const detail=node('button',ui.detail);detail.onclick=()=>navigate(row);actions.append(detail);
      if(!toast&&!row.read_at){const read=node('button',ui.read);read.onclick=async()=>{try{await action(row.id,'read');refresh();}catch(_){note.textContent=ui.offline;}};actions.append(read);}
      article.append(top,description,time,actions);return article;
    };
    const render=()=>{entries.replaceChildren(...items.map(row=>card(row)));if(!items.length)entries.append(node('p',ui.empty));};
    const removeToast=id=>{const active=visible.get(id);if(active){clearTimeout(active.timer);active.el.remove();visible.delete(id);}};
    const pop=row=>{
      if(seen.has(row.id)||row.dismissed_at||row.read_at||row.resolved_at)return;seen.add(row.id);
      if(visible.size>=cfg.toast_limit){note.textContent=ui.overflow;return;}
      const el=card(row,true);el.setAttribute('role',row.severity==='critical'?'alert':'status');
      const state={el,timer:null};visible.set(row.id,state);toasts.append(el);
      if(['info','success'].includes(row.severity)){
        const schedule=()=>{clearTimeout(state.timer);state.timer=setTimeout(()=>removeToast(row.id),cfg.toast_seconds*1000);};
        el.onpointerenter=()=>clearTimeout(state.timer);el.onpointerleave=schedule;el.onfocusin=()=>clearTimeout(state.timer);el.onfocusout=schedule;schedule();
      }
    };
    allRead.onclick=async()=>{allRead.disabled=true;try{await request('/read-all',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({client_id:client,action:'read'})});await refresh();}catch(_){note.textContent=ui.offline;}finally{allRead.disabled=false;}};
    more.onclick=async()=>{try{const data=await request('?'+new URLSearchParams({client_id:client,before:older}));const known=new Set(items.map(row=>row.id));items.push(...data.items.filter(row=>!known.has(row.id)));older=data.before;more.hidden=!older;render();}catch(_){note.textContent=ui.offline;}};
    const schedule=delay=>{clearTimeout(timer);if(!document.hidden&&cfg.enabled)timer=setTimeout(refresh,delay*1000);};
    async function refresh(){
      if(document.hidden||!cfg.enabled)return;if(busy){again=true;return;}busy=true;
      try{
        const data=await request('?'+new URLSearchParams({client_id:client,after:cursor,initial:String(initial)}));
        items=data.items;older=data.before;more.hidden=!older;render();
        bell.querySelector('span').textContent=data.unread?String(data.unread):'';
        bell.setAttribute('aria-label',ui.open+' '+data.unread+' '+ui.unread);
        banner.hidden=!data.critical.length;banner.textContent=data.critical.length?ui.critical_summary+' · '+data.critical[0].title:'';
        position();
        note.textContent=(data.warnings||[]).map(key=>ui[key]).join(' ');
        for(const [id]of visible){const row=items.find(item=>item.id===id);if(row&&(row.resolved_at||row.dismissed_at||row.read_at))removeToast(id);}
        const events=initial?items.filter(row=>['warning','critical'].includes(row.severity)):data.events;
        events.forEach(pop);cursor=data.cursor;initial=false;localStorage.setItem(cursorKey,String(cursor));
        schedule(data.has_more_events?0:cfg.poll_seconds);
      }catch(_){note.textContent=ui.offline;schedule(cfg.backoff_seconds);}finally{busy=false;if(again){again=false;schedule(0);}}
    }
    document.addEventListener('visibilitychange',()=>document.hidden?clearTimeout(timer):refresh());
    window.addEventListener('focus',refresh);
    window.addEventListener('message',event=>{if(event.origin===location.origin&&event.data?.type==='aiquant:notification-refresh'&&Array.from(document.querySelectorAll('iframe.workspace-frame')).some(frame=>frame.contentWindow===event.source))refresh();});
    if(cfg.enabled)refresh();else bell.hidden=true;
  };
  void start();
  new MutationObserver(()=>{if(document.getElementById('workspace-notification-toggle')&&!document.getElementById('notification-center'))start();}).observe(document.body,{childList:true,subtree:true});
}
