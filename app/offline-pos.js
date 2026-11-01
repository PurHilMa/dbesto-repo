/* Browser POS outbox. Permits are server-issued and checked again at receipt. */
window.OfflinePOS=(()=>{
 let db,profile=null,deviceKey=null,syncing=false,forced=false;
 const bytes=new TextEncoder(),text=new TextDecoder();
 const ready=new Promise((resolve,reject)=>{
  const request=indexedDB.open('ebm-offline-pos-v1',1);
  request.onupgradeneeded=()=>{request.result.createObjectStore('meta');request.result.createObjectStore('queue',{keyPath:'id'})};
  request.onsuccess=()=>{db=request.result;resolve()};request.onerror=()=>reject(new Error('Penyimpanan offline tidak tersedia.'));
 });
 function store(name,mode,fn){return new Promise((resolve,reject)=>{const tx=db.transaction(name,mode);let value;try{const r=fn(tx.objectStore(name));if(r)r.onsuccess=()=>{value=r.result}}catch(e){reject(e);return}tx.oncomplete=()=>resolve(value);tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error)})}
 async function get(key){await ready;return store('meta','readonly',s=>s.get(key))}
 async function set(key,value){await ready;return store('meta','readwrite',s=>s.put(value,key))}
 async function getOrSet(name,value){await ready;return new Promise((resolve,reject)=>{const tx=db.transaction('meta','readwrite'),s=tx.objectStore('meta'),r=s.get(name);let chosen;r.onsuccess=()=>{chosen=r.result||value;if(!r.result)s.put(value,name)};tx.oncomplete=()=>resolve(chosen);tx.onerror=()=>reject(tx.error)})}
 async function cryptKey(password,salt){const material=await crypto.subtle.importKey('raw',bytes.encode(password),'PBKDF2',false,['deriveKey']);return crypto.subtle.deriveKey({name:'PBKDF2',hash:'SHA-256',salt:new Uint8Array(salt),iterations:210000},material,{name:'AES-GCM',length:256},false,['encrypt','decrypt'])}
 async function encrypt(key,value){const iv=crypto.getRandomValues(new Uint8Array(12));return {iv:Array.from(iv),data:Array.from(new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv},key,bytes.encode(JSON.stringify(value)))))}}
 async function decrypt(key,value){return JSON.parse(text.decode(await crypto.subtle.decrypt({name:'AES-GCM',iv:new Uint8Array(value.iv)},key,new Uint8Array(value.data))))}
 async function device(){return getOrSet('device',crypto.randomUUID())}
 async function key(){if(!deviceKey){deviceKey=await get('device-key');if(!deviceKey)deviceKey=await getOrSet('device-key',await crypto.subtle.generateKey({name:'AES-GCM',length:256},false,['encrypt','decrypt']))}return deviceKey}
 async function post(path,data,csrf){if(forced)throw new TypeError('Mode uji offline aktif.');const response=await fetch('/api/'+path,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(data),signal:AbortSignal.timeout(8000)});const result=await response.json();if(!response.ok){const e=new Error(result.error||'Sinkronisasi gagal.');e.status=response.status;throw e}return result}
 async function prepare(user,password,csrf){
  await ready;if(!user.permissions.includes('pos')){profile=null;return}
  const result=await post('offline/lease',{device:await device()},csrf);
  profile={user,outlets:result.outlets,lease:result.lease};
  const salt=Array.from(crypto.getRandomValues(new Uint8Array(16)));const derived=await cryptKey(password,salt);
  await set('profile:'+user.username,{salt,encrypted:await encrypt(derived,profile)});await key();
  if(navigator.storage?.persist)navigator.storage.persist().catch(()=>{});
  if('serviceWorker' in navigator){await navigator.serviceWorker.register('/sw.js');await navigator.serviceWorker.ready}
 }
 async function unlock(username,password){
  await ready;const saved=await get('profile:'+username.trim().toLowerCase());if(!saved)throw new Error('Akun belum menyiapkan POS offline pada browser/alamat ini. Login online dahulu.');
  try{profile=await decrypt(await cryptKey(password,saved.salt),saved.encrypted)}catch{throw new Error('Kata sandi offline tidak sesuai.')}
  if(Date.now()/1000>profile.lease.expires){profile=null;throw new Error('Izin offline sudah habis (8 jam simulasi). Login online untuk memperbarui.')}
  await key();return {user:{...profile.user,permissions:['pos','sync','modules']},outlets:profile.outlets};
 }
 async function capture(event){
  await ready;if(!profile)throw new Error('POS offline belum siap. Keluar lalu login online kembali.');
  if(Date.now()/1000>profile.lease.expires)throw new Error('Izin POS offline habis. Login online kembali; antrean lama tetap tersimpan.');
  if(!profile.lease.scope.includes(event.outlet))throw new Error('Outlet tidak termasuk izin offline akun ini.');
  const value={...event,id:crypto.randomUUID(),occurredAt:Date.now()/1000,createdAt:new Date().toISOString()};
  const row={id:value.id,owner:profile.user.username,encrypted:await encrypt(await key(),{event:value,lease:profile.lease}),state:'PENDING',reason:''};
  await store('queue','readwrite',s=>s.add(row));return value;
 }
 async function rows(username){await ready;const all=await store('queue','readonly',s=>s.getAll());const result=[];for(const row of all.filter(r=>r.owner===username)){const payload=await decrypt(await key(),row.encrypted);result.push({...row,event:payload.event})}return result}
 async function sync(username,csrf){
  if(syncing)return {busy:true};syncing=true;let count=0;
  try{for(const row of await rows(username)){
   if(row.state!=='PENDING')continue;
   const payload=await decrypt(await key(),row.encrypted);
   try{const result=await post('offline/sync',payload,csrf);row.state=result.status;row.reason=result.reason;row.receivedAt=result.receivedAt;count++;}
   catch(e){if(e.status===409){row.state='CONFLICT';row.reason=e.message}else throw e}
   delete row.event;await store('queue','readwrite',s=>s.put(row));
  }return {count};}finally{syncing=false}
 }
 async function forget(username){profile=null;await ready;await store('meta','readwrite',s=>s.delete('profile:'+username))}
 return {prepare,unlock,capture,rows,sync,forget,clear:()=>{profile=null},setForced:value=>{forced=value},get forced(){return forced},get lease(){return profile?.lease}};
})();
