"""Grounded local Q&A: no external model or data transmission."""
import re
from datetime import datetime, timezone

def rupiah(value):
    return 'Rp'+format(round(value),',').replace(',','.')

def answer(question, day, user, outlets, events, reviews):
    q=question.lower()
    sources=[]
    def result(text):
        return dict(answer=text,mode='local_rules',businessDate=day,sources=sources,asOf=datetime.now(timezone.utc).isoformat())
    if any(word in q for word in ['password','kata sandi','token','rahasia','database','credential']):
        return result('Saya tidak menampilkan kata sandi, token sesi atau data rahasia. Gunakan menu Akun saya untuk mengganti kata sandi.')
    if any(word in q for word in ['hapus','ubah target','nonaktifkan','jalankan kode']):
        return result('Asisten hanya membaca data. Perubahan harus dilakukan melalui menu aplikasi sesuai kewenangan Anda.')
    sources.append('Pengetahuan EBM: definisi KPI dan aturan review v0.2')
    if any(word in q for word in ['definisi','apa itu','artinya','aturan','deadline']):
        return result('TC adalah jumlah struk, bukan jumlah paket. APC = omset / TC. Target per resto: TC >100, APC >Rp30.000 dan COGS bahan pembentuk produk <70%; target omset berbeda per resto. SPV mereview semua resto pada H+1 sebelum pukul 12.00. Resto sehat memerlukan rata-rata omset harian dalam satu bulan >Rp3 juta dan NPM bulan yang sama ≥10%.')
    if any(word in q for word in ['laba','npm','sehat','inventory','stok','gudang','marketing','okr','pajak','bulan','kemarin','hari ini']):
        return result('Data tersebut belum tersedia atau periodenya belum dapat ditentukan pada simulasi ini. PnL, inventory, marketing dan OKR belum diimplementasikan. Pilih tanggal bisnis yang tepat; saya tidak menyimpulkan laba atau kesehatan bulanan dari omset harian.')
    requested=re.findall(r'ebm-\d{3}',q)
    for label,oid in [('resto a','EBM-001'),('resto b','EBM-002'),('resto c','EBM-003'),('outlet a','EBM-001'),('outlet b','EBM-002'),('outlet c','EBM-003')]:
        if label in q: requested.append(oid.lower())
    available={o['id'].lower() for o in outlets}
    if requested and any(oid not in available for oid in requested):
        return result('Outlet yang diminta tidak tersedia dalam cakupan akses akun Anda. Saya tidak dapat menampilkan datanya.')
    if requested:
        outlets=[o for o in outlets if o['id'].lower() in requested]
        ids={o['id'] for o in outlets}
        events=[e for e in events if e['outlet'] in ids]
        reviews=[r for r in reviews if r['outlet'] in ids]
    prefix=f'Tanggal bisnis {day}. Cakupan: '+(', '.join(o['name'] for o in outlets) or 'tidak ada outlet')+'.\n\n'
    permissions=user['permissions']
    if 'review' in q or 'tinjau' in q or 'temuan' in q:
        if 'review.read' not in permissions:
            return result('Akun Anda tidak mempunyai izin membaca review SPV.')
        sources.append('Review SPV tersimpan, sesuai outlet dan tanggal bisnis')
        done={r['outlet'] for r in reviews}
        text=f'{len(done)} dari {len(outlets)} outlet memiliki draft review. Draft tersimpan belum berarti review disahkan atau tindakan selesai.'
        for r in reviews:
            text+='\n'+r['outlet']+': Temuan: '+r['finding']+'\nTindakan: '+r['action']
        missing=[o['name'] for o in outlets if o['id'] not in done]
        if missing:text+='\nBelum ada review: '+', '.join(missing)+'.'
        return result(prefix+text)
    if 'overview' not in permissions and 'review.read' not in permissions:
        if 'sync' not in permissions:
            return result('Akun Anda belum memiliki izin membaca data penjualan. Modul gudang juga belum tersedia.')
        sources.append('Transaksi kasir lokal sesuai akses akun; tidak termasuk data awal contoh')
        amount=sum(e['amount'] for e in events)
        return result(prefix+f'Transaksi kasir tersimpan: {len(events)} struk, omset {rupiah(amount)}, APC {rupiah(amount/len(events)) if events else "belum ada transaksi"}. Akun ini tidak berizin membaca target dan dashboard agregat.')
    sources.append('Proyeksi operasional lokal: data awal contoh + transaksi kasir pada outlet/tanggal yang dipilih')
    if any(word in q for word in ['cogs','biaya']):
        return result(prefix+'\n'.join(o['name']+': COGS resep contoh '+str(o['cogs'])+'%.' for o in outlets)+'\nAngka tersebut estimasi contoh tetap, belum biaya aktual dari inventory atau pembukuan.')
    if any(word in q for word in ['target','prioritas','terendah','tertinggi','perhatian','banding']):
        return result(prefix+'\n'.join(f"{o['name']}: omset {rupiah(o['sales'])} / target {rupiah(o['target'])}; capaian {o['sales']/o['target']*100:.1f}%; {'kurang '+rupiah(o['target']-o['sales']) if o['sales']<o['target'] else 'target tercapai'}." for o in sorted(outlets,key=lambda o:o['sales']/o['target']))+'\nUrutan berdasarkan pencapaian target terendah. Penyebab penurunan tidak dapat dipastikan hanya dari angka ini.')
    if any(word in q for word in ['omset','omzet','tc','apc','jual','transaksi','ringkas','berapa','struk','pelanggan']):
        total=sum(o['sales'] for o in outlets);tc=sum(o['tc'] for o in outlets);target=sum(o['target'] for o in outlets)
        return result(prefix+f'Omset: {rupiah(total)}. TC: {tc} struk. APC: {rupiah(total/tc) if tc else "belum dapat dihitung (TC nol)"}. Target omset: {rupiah(target)}.\n'+ '\n'.join(f"{o['name']}: {rupiah(o['sales'])}, {o['tc']} struk, APC {rupiah(o['sales']/o['tc']) if o['tc'] else 'belum tersedia'}." for o in outlets)+'\nAngka operasional simulasi; belum laporan pembukuan final.')
    return result('Mode lokal berbasis aturan mendukung pertanyaan omset, TC, APC, target, COGS contoh, review dan definisi KPI. Saya belum memakai model AI generatif. Coba “Ringkas penjualan”, “Outlet mana di bawah target?” atau “Review mana yang belum selesai?”. Pertanyaan di luar cakupan ini belum dapat dijawab secara andal.')
