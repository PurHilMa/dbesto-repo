# ERP PT EBM d’Besto — Kontrak KPI, Persediaan, dan Akuntansi v0.2

Tanggal: 1 November 2026. Status: spesifikasi rancangan untuk review; belum merupakan kebijakan finance yang disahkan. Dokumen induk: [Perencanaan v0.2](ERP-PT-EBM-Perencanaan-v0.2.md). Kontrak platform: [Kontrak Teknis](ERP-EBM-v0.2-Kontrak-Teknis.md).

## 1. Kedudukan dan aturan aktivasi

Dokumen ini menjadi sumber rinci rumus KPI dan dampak transaksi ke persediaan/akuntansi pada paket v0.2. Fakta terkonfirmasi: TC adalah jumlah struk, target TC >100/hari, APC >Rp30.000, COGS bahan pembentuk produk <70%, serta kesehatan bulanan membutuhkan rata-rata omzet harian >Rp3 juta dan NPM ≥10%.

Semua detail metode di bawah merupakan **profil rancangan sandbox `EBM-DESIGN-02`**, belum persetujuan bisnis. Pengembang memakai profil ini untuk contoh dan pengujian; produksi hanya menerima profil berstatus `APPROVED` dan bertanggal berlaku. Profil kosong/draft tidak boleh diam-diam diperlakukan sebagai pajak nol, kepemilikan EBM, atau batas persetujuan tak terbatas.

Kebijakan memiliki `policy_id`, `version`, `scope`, `valid_from`, `valid_to`, `status`, `approved_by`, `approved_at`. Versi disimpan pada transaksi/snapshot. Masa berlaku tidak boleh tumpang tindih untuk kebijakan sejenis pada lingkup sama. Perubahan kebijakan tidak mengubah transaksi lama secara diam-diam.

| Gate | Harus disahkan | Fungsi produksi yang diblokir jika belum lengkap |
|---|---|---|
| FIN-01 | Entitas/buku, pemilik stok, hak pendapatan, COA dan posting rules | Posting resmi, PnL final, transfer antar buku |
| FIN-02 | Pajak, diskon merchant/platform, pendapatan dan refund | Aktivasi profil penjualan produksi |
| FIN-03 | Valuasi, costing produksi, akun waste/variance, mapping COGS 70% | Valuasi final, status resmi COGS, close inventory |
| FIN-04 | Alokasi biaya, laba bersih, denominator kalender, close/reopen | NPM final dan status sehat final |
| FIN-05 | Kontrak pemilik, dasar distribusi, saham, cadangan, persetujuan | Posting kewajiban dan pembayaran bagi hasil |

Modul fondasi dan simulasi tetap dapat dikembangkan setelah ada instruksi coding. Gate diterapkan pada fungsi terkait, bukan alasan menghentikan seluruh perencanaan.

## 2. Penjualan, pengakuan, dan KPI

### 2.1 Identitas dan waktu

- `order_id` mengidentifikasi pesanan; `sale_id` mengidentifikasi struk penjualan sah; `payment_id` dan `refund_id` adalah dokumen terpisah.
- Default R1: satu order menjadi satu sale saat seluruh pemenuhan penjualan dikonfirmasi. Split payment tidak menambah TC. Pemenuhan sebagian dicatat sebagai order terpisah bila dibutuhkan R1; dilarang menggandakan satu item terpenuhi.
- Simpan `occurred_at`, `business_date`, `received_at`, `posting_date`, `posted_at`, `source_sale_id`, serta versi kebijakan. Definisi zona/hari usaha mengikuti profil induk yang disahkan. `posted_at` adalah waktu server membukukan; `posting_date` adalah tanggal buku, bukan tanggal jam server.
- Pesanan draft, void sebelum pemenuhan, deposit, payment retry, invoice ulang, dan dokumen refund tidak menciptakan sale baru.
- Transaksi sah yang datang terlambat tetap diingest, lalu menjalani prosedur periode terbuka/tertutup. Waktu penerimaan server tidak mengganti tanggal kejadian aslinya.

**Basis periode profil DESIGN:** MET-01 sampai MET-08 menggunakan `posting_date` transaksi yang sudah `POSTED`. Untuk sale normal, `posting_date = business_date` saat pemenuhan, termasuk sinkron H+1 selama periode asal masih terbuka. TC dikelompokkan pada tanggal buku sale yang sama dengan revenue sale tersebut. Credit note memakai tanggal buku koreksi yang disetujui; pembayaran refund tidak mengubah KPI lagi.

Jika periode asal sudah tertutup, finance memilih reopen atau posting adjustment di periode terbuka. Dalam pilihan adjustment, sale dan satu efek TC berada pada periode buku adjustment; laporan wajib memisahkan penjualan hari berjalan dan koreksi periode lama agar pencapaian dapat dijelaskan. `business_date` asal tetap tersedia. Ini pilihan profil rancangan yang memerlukan pengesahan D01; bukan klaim bahwa semua struk terjadi pada tanggal buku. Laporan kejadian berdasarkan `business_date` memiliki label berbeda dan rekonsiliasi ke laporan buku; tidak mengganti KPI resmi diam-diam.

Sale yang baru tersimpan/diterima server tetapi belum posted tampil sebagai transaksi tertunda dengan estimasi terpisah; tidak masuk total final atau TC final. Review H+1 memperlihatkan ketidaklengkapan tersebut. Kasir tidak boleh memilih tanggal buku untuk memindahkan pencapaian target; tanggal ditentukan aturan periode dan otorisasi finance.

### 2.2 Profil metrik deterministik

| ID | Nama dan formula default sandbox | Ketentuan |
|---|---|---|
| MET-01 | Gross sales = jumlah nilai item terpenuhi sebelum diskon merchant, tanpa pajak titipan | Harga termasuk pajak dipecah menurut konfigurasi yang disahkan |
| MET-02 | Net sales = gross sales − merchant discount − approved sales credit notes pada periode | Refund mengurangi sales saat credit note diposting; pembayaran refund tidak mengurangi sales lagi |
| MET-03 | TC = distinct `sale_id` terpenuhi dan posted, dikelompokkan menurut `posting_date` | Refund tidak mengurangi TC historis; refund-only tidak menambah TC; koreksi periode lama ditandai |
| MET-04 | APC arus periode = net sales periode / TC periode | TC=0 → NULL + alasan `NO_SALES_RECEIPTS`; TC>0 menghasilkan angka bertanda, termasuk negatif |
| MET-05 | Pencapaian omzet = net sales / target omzet ×100% | Target harus >0; target kosong/nol → NULL + alasan |
| MET-06 | Rata-rata omzet bulanan = net sales bulan / hari denominator | Default rancangan: hari kalender dalam interval resto aktif; tutup sementara dihitung; data hilang bukan nol |
| MET-07 | NPM = approved net profit / net sales ×100% | Net sales ≤0 → NULL + alasan `NON_POSITIVE_REVENUE`; tidak memberi status sehat |
| MET-08 | COGS % = biaya dalam mapping KPI disetujui / net sales ×100% | Net sales ≤0 atau mapping belum disetujui → NULL + alasan |

APC negatif dengan TC>0 tetap ditampilkan dan berada di bawah target, disertai penanda periode didominasi refund. APC ini bukan ukuran nilai pembelian cohort pelanggan; rincian gross sales, diskon, credit note, dan TC ditampilkan bersama. Penghitungan ulang refund ke tanggal struk asal hanya boleh menjadi laporan analitik terpisah, bernama jelas, dan tidak mengganti KPI arus periode.

Hari aktif untuk MET-06 mencakup tanggal mulai sampai akhir aktif, secara inklusif. Bulan pertama/terakhir diberi penanda `PARTIAL_MONTH`; angka dibandingkan ambang yang sama pada profil rancangan. Perubahan kalender membutuhkan approval. Resto sementara tutup tetap memiliki hari aktif; outlet yang tidak aktif sepanjang periode tidak masuk denominator jaringan.

Net sales mencatat hak ekonomi penjualan, bukan uang settlement neto. Komisi kanal dan biaya pembayaran menjadi biaya terpisah. Subsidi pihak ketiga membutuhkan aturan hak pendapatan/receivable tersendiri; tidak otomatis disamakan diskon merchant atau pendapatan.

### 2.3 Refund dan periode

1. Sebelum fulfillment: batalkan order; lepaskan reservasi; jika deposit sudah diterima, selesaikan kewajiban pengembalian. Tidak ada revenue/TC.
2. Sesudah fulfillment: credit note wajib merujuk sale dan item/jumlah, approval, alasan, serta pajak terkait. Kredit tidak boleh melebihi sisa nilai item yang belum dikreditkan.
3. Posting credit note mengurangi revenue pada tanggal posting, menciptakan kewajiban refund atau mengurangi piutang. Pembayaran refund hanya menyelesaikan kewajiban tersebut.
4. Full/partial refund tidak otomatis mengembalikan bahan atau ayam matang ke stok saleable. Keputusan finansial dan disposisi fisik terpisah.
5. Pengembalian barang fisik yang disetujui masuk lokasi/status karantina; pemulihan nilai menggunakan biaya historis terkait sesuai kebijakan. Penjualan kembali hanya setelah release berwenang.
6. Periode sumber tertutup: transaksi koreksi masuk antrean finance. Pilih posting periode terbuka dengan referensi asal, atau reopen resmi. Dilarang otomatis mengubah PnL final.

### 2.4 Status dan agregasi

Perbandingan ambang memakai angka presisi, bukan angka yang sudah dibulatkan untuk layar. TC=100 belum memenuhi; APC=30.000 belum memenuhi; COGS=70% belum memenuhi; NPM=10% memenuhi; rata-rata omzet=3.000.000 belum memenuhi.

APC agregat = total net sales / total TC; NPM/COGS agregat memakai total komponen. Total jaringan diberi jumlah resto eligible, data lengkap, data hilang, serta bulan parsial. Jangan menyajikan gabungan sebagian sebagai seluruh 220 resto.

Status kesehatan final dihitung hanya bila data sales dan PnL bulan sama lengkap, profil approved, periode final, serta denominator sah. Target omzet individual tetap terpisah dari ambang kesehatan.

## 3. Food cost versus ledger COGS

Untuk PT EBM, target 70% berbicara bahan pembentuk produk. Itu belum menentukan seluruh komponen cost of sales pembukuan. Sistem menyimpan komponen terpisah agar finance dapat mengesahkan mapping tanpa mengganti histori.

| Bucket | Definisi | Dampak |
|---|---|---|
| `FOOD_SOLD` | Komponen biaya bahan pada unit yang dijual | Cost of sales bahan |
| `FOOD_WASTE` | Kerugian bahan/produk yang diakui terpisah | Beban waste, tidak sekaligus dipotong sebagai penjualan |
| `FOOD_VARIANCE` | Selisih opname/revaluasi bahan yang disetujui | Beban/pendapatan penyesuaian sesuai arah dan akun |
| `CONVERSION_SOLD` | Tenaga kerja/overhead produksi yang dikapitalisasi dan melekat pada produk terjual | Komponen cost of sales nonbahan jika kebijakan mengizinkan |
| `OTHER_OPEX` | Biaya operasional yang tidak masuk persediaan | Beban periode |
| `RECIPE_THEORETICAL` | Kuantitas standar × biaya referensi untuk penjualan | Analitik; tidak membuat jurnal atau stok kedua |

Usulan profil KPI bahan: `FOOD_SOLD + FOOD_WASTE + FOOD_VARIANCE` dibagi net sales. Setiap baris biaya hanya masuk sekali berdasarkan `cost_component_id`; variance bertanda dikontrol persetujuan. Nama layar: **COGS bahan — termasuk waste dan selisih** bila profil ini dipilih. Status pencapaian 70% tetap diblokir sebelum CEO/finance menyetujui komponen.

Penambahan waste dan selisih merupakan perluasan usulan atas bahan produk terjual; pengguna belum menyetujui perluasan tersebut. Alternatif mapping `FOOD_SOLD` saja diberi nama berbeda dan tetap menampilkan waste terpisah. Developer tidak memilih salah satu tanpa policy approved.

Waste normal proses yang sudah terserap ke biaya unit hasil tidak dicatat lagi sebagai beban terpisah. Waste abnormal atau waste produk jadi setelah produksi dicatat terpisah sesuai kebijakan. Perbandingan teori/aktual menunjukkan perubahan harga, yield, waste, mix, serta selisih; tidak menyimpulkan semua selisih sebagai kehilangan.

## 4. Persediaan dan produksi

### 4.1 Cost pool dan valuasi

Usulan metode: perpetual inventory dengan moving weighted average. Cost pool minimum: `(inventory_owner_id, accounting_book_id, location_id, item_id, currency)`. Batch fisik tetap disimpan untuk traceability/expiry; FEFO fisik tidak mengubah metode biaya rata-rata.

Setiap komponen bahan/conversion membawa nilai terpisah dalam pool. Penerimaan memperbarui average: `(nilai sebelum + nilai penerimaan) / (qty sebelum + qty penerimaan)`. Pengeluaran memakai unit cost sebelum pengeluaran. Cost pool berbeda tidak dicampur hanya karena lokasi atau SKU terlihat sama.

Landed cost dan invoice variance dialokasikan berdasarkan profil yang disahkan. Jika bahan sudah terjual, penyesuaian dibagi ke persediaan tersisa dan beban terkait dengan jejak alokasi; tidak seluruhnya dibebankan pada stok tersisa tanpa aturan. Metode dan replay transaksi mundur tidak boleh diubah ketika periode sudah ditutup.

### 4.2 Pilihan pengeluaran bahan

| Metode item/lokasi | Kapan bahan keluar | Kapan cost of sales muncul |
|---|---|---|
| `BATCH_PRODUCTION` | Saat issue bahan ke work in process | Saat unit hasil dijual; bahan tidak dikurangi ulang |
| `DIRECT_RECIPE` | Saat fulfillment sale berdasarkan recipe version | Bersamaan dengan pengeluaran bahan saat sale |
| `DIRECT_STOCK` | Saat fulfillment item stok siap jual | Bersamaan dengan pengeluaran item itu |

Metode dibekukan pada dokumen sumber, berlaku melalui tanggal efektif, dan tidak dipilih ad hoc oleh kasir. Pergantian metode membutuhkan penghentian batch aktif, rekonsiliasi stok, serta persetujuan master. Komponen paket mengacu produk/metode masing-masing; penjualan paket tidak mengeluarkan parent nonstok dan seluruh komponen sekaligus.

Konversi kg, ekor, potong, karton, dan kemasan wajib eksplisit. kg→potong yang bergantung hasil pemotongan adalah output produksi/yield, bukan konversi tetap. Batch pemotongan dapat menghasilkan beberapa item; dasar alokasi biaya tiap output harus disahkan. R1 dapat membatasi satu output per batch sampai aturan multi-output tersedia.

Jika pilot menerima ayam utuh dan menghasilkan beberapa jenis potongan, multi-output menjadi dependency R1 untuk lokasi tersebut. Lokasi tidak boleh diluluskan menggunakan konversi palsu atau dipaksa satu output. Alternatif cakupan pilot adalah proses yang menerima potongan siap pakai, dengan batas tertulis dan disetujui.

### 4.3 Transfer dan opname

- Pengiriman internal membuat dua pergerakan atomik: keluar lokasi asal, masuk transit dengan pemilik/buku tetap. Penerimaan memindah transit ke tujuan.
- Penerimaan sebagian menyisakan transit. Kekurangan tidak otomatis dihapus; penyelesaian berupa penerimaan lanjutan, retur, atau write-off berapproval.
- Transfer lintas pemilik/buku tidak memakai dokumen internal biasa. Perlu purchase/sale atau dokumen antar pihak sesuai kebijakan dan eliminasi yang disahkan.
- Opname menghitung kuantitas pada cutoff dan movement yang masuk sesudah cutoff. Hasil hitung bukan langsung saldo; variance dibuat sesudah rekonsiliasi dan approval.
- Stok negatif online diblokir. Sale offline yang sudah nyata terjadi tidak dihapus karena stok server kurang; terima ke antrean cost/stock exception, blokir finalisasi terkait sampai resolusi.
- PnL/COGS tidak boleh final ketika movement bernilai belum terselesaikan. Dashboard menampilkan pendapatan tersedia dengan COGS belum lengkap.

## 5. Presisi dan pembulatan profil sandbox

- Kuantitas dasar: decimal 18,6; unit cost: decimal 24,8; nilai inventory internal: decimal 24,8. Tidak memakai binary float.
- Nilai dokumen/jurnal IDR: decimal 20,2, pembulatan HALF_UP ke Rp0,01. Harga/tender kas dapat dibatasi rupiah bulat; selisih tender dibukukan di akun rounding tersendiri.
- Setiap alokasi menghitung pada presisi internal lalu membagi sisa Rp0,01 dengan largest remainder; tie-break berdasarkan ID baris stabil. Jumlah hasil wajib sama dengan nilai sumber.
- Saat seluruh qty pool habis, pengeluaran terakhir mengambil seluruh residual nilai pool sehingga qty=0 berarti nilai=0. Negative cost/qty exceptions tidak diselesaikan dengan memaksa nilai nol.
- Jurnal harus seimbang pada precision posting. Ketidakcocokan di atas hasil pembulatan sah menghasilkan exception, bukan balancing account otomatis tanpa alasan.

## 6. Matriks event → jurnal rancangan

Contoh tanpa pajak dan tanpa biaya tambahan; account names adalah logical mapping, bukan nomor COA final. Seluruh posting menyimpan source event unik, entitas/buku, lokasi, periode, approval, versi aturan, dan reversal reference.

| Event | Debit | Kredit | Syarat/titik posting |
|---|---|---|---|
| Terima barang dari supplier | Inventory | GRNI/barang diterima belum ditagih | Penerimaan disetujui; nilai berdasarkan PO approved |
| Invoice cocok penerimaan | GRNI | Utang supplier | Quantity/value match; variance punya aturan tersendiri |
| Bayar supplier | Utang supplier | Bank/payment clearing | Pembayaran terverifikasi; clearing direkonsiliasi ke bank |
| Deposit pelanggan | Bank/payment clearing | Uang muka pelanggan | Dana diterima; belum revenue |
| Fulfillment sale | Kas/receivable | Revenue | Hanya fulfillment sah; pembayaran gagal tidak menjadi kas |
| Terapkan deposit | Uang muka pelanggan | Receivable pelanggan | Tidak menambah revenue |
| Settlement kanal | Bank + biaya kanal | Receivable kanal | Komponen bruto, fee, subsidi, refund dapat direkonsiliasi |
| Sales credit note | Kontra revenue | Refund payable atau receivable | Kredit disetujui; bukan otomatis return inventory |
| Bayar refund | Refund payable | Bank/kas | Satu penyelesaian; retry tidak menggandakan |
| Issue bahan produksi | Work in process | Raw material inventory | Nilai komponen aktual |
| Selesai produksi | Finished goods inventory | Work in process | Qty/yield dan alokasi komponen disahkan |
| Produk terjual | COGS per komponen | Finished goods inventory | Tidak issue bahan kedua kali |
| Direct recipe sale | COGS bahan | Raw material inventory | Hanya item bermetode direct recipe |
| Waste terpisah | Beban waste | Inventory | Tidak terduplikasi dengan waste terserap yield |
| Selisih opname kurang | Beban selisih | Inventory | Setelah recount/investigasi dan approval |
| Selisih opname lebih | Inventory | Akun penyesuaian persediaan | Valuasi serta sumber disetujui |
| Internal transfer | Inventory transit/tujuan | Inventory asal/transit | Reklasifikasi lokasi; tidak membuat revenue |
| Retur supplier | GRNI/receivable supplier | Inventory | Bergantung status invoice dan credit note supplier |
| Pembagian laba disetujui | Laba ditahan/distribution clearing sesuai buku | Utang pembagian | Sesuai hak dan kebijakan; bukan otomatis beban operasi |
| Bayar pembagian | Utang pembagian | Bank | Sesuai nominal kewajiban yang belum dibayar |

Jurnal ledger COGS dapat memiliki komponen conversion; KPI food cost mengambil hanya komponen yang dipetakan. Beban alokasi pusat, biaya pengelolaan, pajak, kerugian, dan distribusi laba tidak boleh dicampur dalam satu akun tanpa definisi PnL.

Posting yang sudah selesai bersifat immutable; reversal adalah event baru. Operational event, stock ledger, inventory valuation, dan finance ledger harus mempunyai hubungan 1:n terkontrol; satu source event dengan posting rule version tidak boleh di-posting dua kali.

Keunikan efek bisnis mengikuti kontrak teknis `(tenant_id, source_event_id, effect_type, ledger_scope)`; versi posting rule disimpan sebagai bukti, bukan cara membuat posting kedua atas event yang sama. Mengubah versi rule memerlukan correction/reversal event baru bila hasil terdahulu memang perlu dikoreksi.

## 7. Titip kelola dan penutupan

Penjualan 220 resto merupakan pandangan operasional jaringan. Pengakuan pendapatan legal PT EBM mengikuti kontrak dan kebijakan yang disahkan, tidak otomatis sama dengan total penjualan jaringan. Management reporting book dan legal accounting book diberi label dan akses berbeda.

Komposisi saham memiliki interval efektif dan total 100% pada scope hak yang sama. Saham, pemilik bahan, pemilik rekening, dan hak pengelola dapat berbeda sehingga memiliki field terpisah. Perubahan tengah periode memakai aturan kontrak yang dipilih; tanpa aturan, distribusi periode tersebut diblokir.

Dasar usulan distribusi: laba periode disetujui + penyesuaian kontraktual − cadangan − kerugian yang harus dipulihkan. Nilai negatif tidak menghasilkan kewajiban pembagian; perlakuan carry-forward mengikuti kontrak. Saldo kas membatasi jadwal bayar, bukan mengubah hak yang sudah disetujui tanpa keputusan baru.

Close mensyaratkan seluruh perangkat/kanal dilaporkan, settlement direkonsiliasi, invoice/GRNI diperiksa, stok/valuasi/WIP lengkap, accrual dan alokasi selesai, serta semua jurnal seimbang. Semua pengecualian harus diselesaikan atau diakui melalui prosedur finance yang disahkan; tidak disembunyikan dari PnL.

Snapshot final menyimpan policy version, source cutoff, ledger revision, approver, dan timestamp. Reopen membuat versi final baru; laporan lama tetap tersedia dan tidak diberi label versi terkini.

## 8. Kasus penerimaan numerik

Seluruh angka rekaan, untuk fixture pengujian; tidak mewakili kinerja atau kontrak PT EBM. Semua contoh tanpa pajak kecuali disebutkan.

Rilis pengujian: ACC-01–ACC-09 dan ACC-11–ACC-14 adalah R1; ACC-10 dan seluruh skenario distribusi/saham adalah R2. Tidak dijalankannya uji R2 tidak menggagalkan R1 jika fitur terkait nonaktif. Semua kasus adalah spesifikasi hasil yang diharapkan, bukan laporan test aplikasi yang sudah dijalankan.

| ID | Input | Hasil wajib |
|---|---|---|
| ACC-01 | Dua sale Rp100.000 dan Rp60.000; credit note parsial Rp20.000 atas sale Rp60.000 pada hari sama | Net sales Rp140.000; TC 2; APC Rp70.000 |
| ACC-02 | Hari berikut refund Rp100.000 tanpa sale baru | Net sales −Rp100.000; TC 0; APC NULL; NPM/COGS ratio NULL; TC hari asal tetap 2 |
| ACC-03 | Gross Rp120.000, diskon merchant Rp20.000, fee kanal Rp20.000 | Revenue Rp100.000; biaya kanal Rp20.000; settlement Rp80.000 |
| ACC-04 | Deposit Rp30.000 untuk sale Rp100.000 | Saat deposit revenue/TC=0; saat fulfillment revenue Rp100.000, TC 1; terapkan deposit, sisa receivable Rp70.000 |
| ACC-05 | 100 kg @Rp30.000; terima 50 kg @Rp36.000 | Qty 150 kg; nilai Rp4.800.000; average Rp32.000/kg |
| ACC-06 | Dari ACC-05 kirim 40 kg, diterima 39 kg | Nilai transit awal Rp1.280.000; tujuan Rp1.248.000; transit tersisa Rp32.000 hingga diselesaikan |
| ACC-07 | Bahan Rp320.000 + pendukung Rp60.000 menghasilkan 20 potong; jual 16, waste 2 | Batch Rp380.000; cost sold Rp304.000; waste Rp38.000; saldo 2 potong/Rp38.000; total tetap Rp380.000 |
| ACC-08 | ACC-07 revenue Rp500.000; semua komponen contoh adalah bahan | Food sold 60,8%; food sold+waste 68,4%; teori terpisah. Status 70% hanya memakai mapping approved |
| ACC-09 | Penerimaan Rp100.000; invoice cocok; bayar Rp100.000 | Inventory +Rp100.000; GRNI kembali nol; AP kembali nol; kas −Rp100.000; bukan expense pembelian langsung |
| ACC-10 | Laba Rp10 juta; cadangan disetujui Rp2 juta; saham 60/40 | Distributable Rp8 juta; hak Rp4,8 juta dan Rp3,2 juta; jumlah tepat Rp8 juta |
| ACC-11 | Nilai Rp100 dialokasikan sama ke tiga baris | Rp33,34; Rp33,33; Rp33,33 menurut tie-break ID; total Rp100,00 |
| ACC-12 | Retry event sale dan settlement masing-masing tiga kali | Satu sale, satu efek TC, satu posting per event; tidak ada duplikasi kas/stok/jurnal |
| ACC-13 | Refund makanan sudah dikonsumsi | Credit note/refund berlaku; tidak menambah stok atau membalik food cost otomatis |
| ACC-14 | Invoice harga berbeda atau recipe version kosong | Exception terlihat; tidak memakai harga/resep nol; periode terdampak belum dapat final |

Uji batas tambahan: revenue nol/negatif, target nol, data hilang, bulan parsial, review tepat pukul 12.00, full refund lintas bulan, transfer beda pemilik, stok offline kurang, late event ke periode final, output produksi nol, perubahan saham tengah periode, dan pembayaran bagi hasil parsial.

### 8.1 Rekonsiliasi contoh batch

Contoh ACC-07 adalah waste produk jadi setelah batch selesai, bukan waste normal proses yang terserap yield:

1. Issue bahan: Dr WIP Rp380.000; Cr bahan Rp380.000.
2. Selesai 20 potong: Dr produk jadi Rp380.000; Cr WIP Rp380.000.
3. Jual 16 potong: Dr food COGS Rp304.000; Cr produk jadi Rp304.000.
4. Waste 2 potong: Dr food waste Rp38.000; Cr produk jadi Rp38.000.
5. Sisa 2 potong senilai Rp38.000; WIP nol. Tidak ada issue bahan tambahan pada langkah 3.

### 8.2 Rekonsiliasi settlement dan deposit

ACC-03: Dr receivable kanal Rp100.000 / Cr revenue Rp100.000; kemudian Dr bank Rp80.000 + Dr biaya kanal Rp20.000 / Cr receivable kanal Rp100.000. Piutang kembali nol dan omzet tetap Rp100.000.

ACC-04: Dr bank Rp30.000 / Cr uang muka Rp30.000; saat fulfillment Dr receivable Rp100.000 / Cr revenue Rp100.000; gunakan deposit dengan Dr uang muka Rp30.000 / Cr receivable Rp30.000; pelunasan Dr bank Rp70.000 / Cr receivable Rp70.000. Kas diterima total Rp100.000, bukan Rp130.000. Sale tunai serentak boleh memakai pasangan kas/revenue langsung hanya bila penerimaan kas belum dibukukan sebelumnya.

## 9. Referensi prinsip dan batas penerapan

Ringkasan resmi IAS 2 membahas biaya persediaan, formula FIFO/rata-rata tertimbang, serta pengakuan nilai persediaan sebagai beban ketika barang dijual. Ini mendukung pemisahan biaya persediaan, harga beli, dan cost of sales dalam rancangan. Rujukan tersebut tidak menetapkan profil perpajakan, penerapan standar lokal, atau perlakuan titip kelola PT EBM; penetapannya tetap melalui finance yang berwenang. [IFRS Foundation — IAS 2 Inventories](https://www.ifrs.org/issued-standards/list-of-standards/ias-2-inventories/), diakses 1 November 2026.

Tidak ada klaim bahwa pemilihan metode rancangan ini merupakan sertifikasi kepatuhan. Persetujuan profil dan contoh UAT merupakan bagian dari kesiapan fungsi sebelum operasi nyata.
