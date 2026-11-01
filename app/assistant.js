(() => {
  let context=null,identity='',generation=0;
  const style=document.createElement('style');
  style.textContent=`#ebm-assistant{position:fixed;right:20px;bottom:20px;z-index:30}#ebm-ai-toggle{box-shadow:0 4px 20px #0002}#ebm-ai-panel{width:min(390px,calc(100vw - 24px));max-height:calc(100dvh - 100px);display:flex;flex-direction:column;background:#fff;border:1px solid #e6e4e1;border-radius:14px;box-shadow:0 12px 45px #0002;margin-bottom:10px;overflow:hidden}#ebm-ai-panel header{padding:14px 16px}#ebm-ai-panel h2{margin:0;font-size:16px}#ebm-ai-log{overflow:auto;max-height:310px;padding:16px;white-space:pre-wrap;overflow-wrap:anywhere;font-size:14px;line-height:1.6}#ebm-ai-log p{margin:0 0 14px}#ebm-ai-log small{display:block;font-size:12px;margin-top:6px}#ebm-ai-panel form{padding:0 16px 16px}#ebm-ai-question{min-height:66px;max-height:140px;resize:vertical}#ebm-ai-send{margin-top:8px;width:100%}#ebm-ai-date{padding:10px 16px;background:#f7f7f5;font-size:12px;color:#6c6a70}@media(max-width:650px){#ebm-assistant{right:12px;bottom:12px}body{padding-bottom:65px}}`;
  document.head.append(style);
  const host=document.createElement('aside');host.id='ebm-assistant';host.hidden=true;host.setAttribute('aria-label','Asisten AI EBM');
  host.innerHTML='<section id="ebm-ai-panel" hidden aria-labelledby="ebm-ai-heading"><header><div><h2 id="ebm-ai-heading">Asisten AI EBM</h2><small>Mode lokal · berbasis aturan</small></div><button id="ebm-ai-close" aria-label="Tutup asisten">Tutup</button></header><div id="ebm-ai-date"></div><div id="ebm-ai-log" role="log" aria-live="polite"></div><form><label for="ebm-ai-question">Pertanyaan tentang data EBM</label><textarea id="ebm-ai-question" maxlength="1000" required placeholder="Contoh: Berapa omset dan TC?"></textarea><button id="ebm-ai-send" class="primary">Kirim pertanyaan</button><p id="ebm-ai-error" role="status"></p></form></section><button id="ebm-ai-toggle" class="primary" aria-expanded="false" aria-controls="ebm-ai-panel">✦ Asisten AI</button>';
  document.body.append(host);
  const panel=host.querySelector('#ebm-ai-panel'),toggle=host.querySelector('#ebm-ai-toggle'),log=host.querySelector('#ebm-ai-log'),input=host.querySelector('textarea'),send=host.querySelector('#ebm-ai-send'),error=host.querySelector('#ebm-ai-error');
  function close(){panel.hidden=true;toggle.setAttribute('aria-expanded','false');toggle.focus()}
  function append(label,text,sources=[]){const p=document.createElement('p');const b=document.createElement('strong');b.textContent=label+'\n';p.append(b,document.createTextNode(text));if(sources.length){const s=document.createElement('small');s.textContent='Sumber: '+sources.join(' · ');p.append(s)}log.append(p);log.scrollTop=log.scrollHeight}
  toggle.onclick=()=>{if(panel.hidden){panel.hidden=false;toggle.setAttribute('aria-expanded','true');input.focus()}else close()};host.querySelector('#ebm-ai-close').onclick=close;
  host.onkeydown=e=>{if(e.key==='Escape')close()};
  window.addEventListener('ebm:session',event=>{
    const next=event.detail;const key=next?.user?.username||'';
    if(key!==identity||next?.date!==context?.date){generation++;log.replaceChildren();append('EBM','Tanyakan omset, TC, APC, target, atau review pada tanggal terpilih. Jawaban hanya memakai data yang boleh Anda akses. Mode lokal ini belum memakai model AI generatif.');input.value='';error.textContent='';send.disabled=false}
    identity=key;context=next;host.hidden=!key;
    if(!key){panel.hidden=true;toggle.setAttribute('aria-expanded','false')}
    host.querySelector('#ebm-ai-date').textContent='Tanggal bisnis: '+(next?.date||'—')+' · Data simulasi lokal';
  });
  host.querySelector('form').onsubmit=async event=>{
    event.preventDefault();const question=input.value.trim();if(!question||!context?.user)return;
    const current=generation;append('Anda',question);input.value='';send.disabled=true;error.textContent='Membaca data sesuai akses Anda…';
    try{
      const response=await fetch('/api/assistant',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':context.csrf},body:JSON.stringify({question,businessDate:context.date})});
      const result=await response.json();if(current!==generation)return;
      if(!response.ok)throw new Error(result.error||'Gagal membaca data.');
      append('Asisten EBM',result.answer,[...(result.sources||[]),'Tanggal '+result.businessDate]);error.textContent='';
    }catch(e){if(current===generation)error.textContent=e.message}
    finally{if(current===generation){send.disabled=false;input.focus()}}
  };
})();
