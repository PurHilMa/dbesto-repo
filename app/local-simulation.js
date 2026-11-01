/* Local simulation controls. Never sends data to an external service. */
(() => {
  const open = indexedDB.open('ebm-development', 1);
  let db;
  open.onsuccess = () => { db = open.result; };
  const tools = document.createElement('section');
  tools.className = 'panel';
  tools.style.cssText = 'max-width:1152px;margin:20px auto;padding:22px';
  tools.innerHTML = `<h2>Laboratorium lokal</h2>
    <p class="muted">Simulasikan pengiriman transaksi ke pusat pada komputer ini. Hasil simulasi bukan bukti penerimaan server produksi.</p>
    <div style="display:flex;gap:10px;flex-wrap:wrap">
      <button id="ebm-sync">Simulasikan penerimaan pusat</button>
      <button id="ebm-backup">Ekspor cadangan JSON</button>
      <label style="margin:0">Pulihkan cadangan <input id="ebm-restore" type="file" accept="application/json,.json"></label>
    </div><p id="ebm-message" role="status" aria-live="polite"></p>`;
  document.body.append(tools);
  const message = text => { document.getElementById('ebm-message').textContent = text; };
  const read = store => new Promise((resolve, reject) => {
    const r = db.transaction(store).objectStore(store).getAll();
    r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error);
  });
  const ready = () => { if (!db) throw new Error('Penyimpanan belum siap. Coba lagi.'); };
  document.getElementById('ebm-sync').onclick = async () => {
    try {
      ready(); const events = await read('events');
      await new Promise((resolve, reject) => {
        const tx = db.transaction('events', 'readwrite');
        events.forEach(event => {
          if (!event.simulatedReceiptAt) tx.objectStore('events').put({...event, simulatedReceiptAt: new Date().toISOString()});
        });
        tx.oncomplete = resolve; tx.onerror = () => reject(tx.error);
      });
      message(`${events.length} transaksi memiliki receipt simulasi lokal. Status transaksi produksi tetap menunggu pusat.`);
    } catch (error) { message(error.message); }
  };
  document.getElementById('ebm-backup').onclick = async () => {
    try {
      ready(); const backup = {format:'ebm-local-v1', exportedAt:new Date().toISOString(), events:await read('events'), reviews:await read('reviews')};
      const url = URL.createObjectURL(new Blob([JSON.stringify(backup, null, 2)], {type:'application/json'}));
      const a = document.createElement('a'); a.href = url; a.download = 'ebm-simulasi-cadangan.json'; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000); message('Cadangan diunduh. Simpan file untuk memulihkan data lokal.');
    } catch (error) { message(error.message); }
  };
  document.getElementById('ebm-restore').onchange = async event => {
    try {
      ready(); const file = event.target.files[0]; if (!file) return;
      if (file.size > 5000000) throw new Error('Batas file cadangan 5 MB.');
      const data = JSON.parse(await file.text());
      if (data.format !== 'ebm-local-v1' || !Array.isArray(data.events) || !Array.isArray(data.reviews)) throw new Error('Format cadangan tidak sesuai.');
      for (const row of data.events) {
        if (typeof row.id !== 'string' || typeof row.createdAt !== 'string' || !Number.isSafeInteger(row.amount) || row.amount < 0 || !Number.isSafeInteger(row.quantity) || row.quantity < 1) throw new Error('Data transaksi tidak valid.');
      }
      for (const row of data.reviews) {
        if (typeof row.id !== 'string' || typeof row.outlet !== 'string' || typeof row.finding !== 'string' || typeof row.action !== 'string') throw new Error('Data review tidak valid.');
      }
      await new Promise((resolve, reject) => {
        const tx = db.transaction(['events','reviews'], 'readwrite');
        data.events.forEach(row => tx.objectStore('events').put(row));
        data.reviews.forEach(row => tx.objectStore('reviews').put(row));
        tx.oncomplete = resolve; tx.onerror = () => reject(tx.error); tx.onabort = () => reject(tx.error);
      });
      message('Cadangan digabungkan berdasarkan ID. Muat ulang halaman untuk memperbarui tampilan.');
    } catch (error) { message(error.message); }
    finally { event.target.value = ''; }
  };
})();
