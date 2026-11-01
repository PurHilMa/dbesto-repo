# ERP PT EBM d’Besto v0.2 — Kontrak Operasional dan UAT

Tanggal: 1 November 2026. Status: spesifikasi perencanaan untuk review, belum izin coding atau kebijakan operasional yang disahkan.

Dokumen induk: [Perencanaan v0.2](ERP-PT-EBM-Perencanaan-v0.2.md). Rumus transaksi dan keuangan: [KPI dan Akuntansi](ERP-EBM-v0.2-KPI-dan-Akuntansi.md).

## 1. Status aturan dan batas rilis

- **CONFIRMED:** 220 resto PT EBM; target CEO; SPV mereview setiap resto pada H+1 sebelum 12.00; ACM memeriksa SPV dan melakukan sampling; kesehatan bulanan mengikuti dua ambang yang diberikan pengguna.
- **PROPOSED DEFAULT:** kontrak deterministik di bawah untuk dibahas. Dapat dipakai menyusun schema, prototype, dan pengujian setelah instruksi implementasi, tetapi bukan bukti persetujuan kebijakan.
- **BUSINESS GATE:** parameter bisnis belum ditetapkan; fitur terkait tidak boleh diam-diam menggunakan nilai contoh di produksi.
- **DEFERRED:** fitur berada di rilis berikutnya dan tidak menjadi syarat go-live rilis sebelumnya selama tidak diaktifkan.

Pemetaan ke dokumen induk: **DESIGN = PROPOSED DEFAULT**, **GATED = BUSINESS GATE**. Kedua pasangan adalah label sinonim, bukan tingkat persetujuan berbeda.

R1A mencakup fondasi, login, target/review dasar dengan fixture simulasi. R1C mencakup kesehatan, review, tindakan, pemeriksaan ACM, sampling dasar, dan pilot terintegrasi dengan transaksi R1B. Label R1 pada UAT berarti core yang harus lulus sebelum go-live R1 operasional, bukan semuanya wajib selesai pada R1A. R2 mencakup OKR, aturan sampling lanjutan, serta bagi hasil sesuai dokumen finance. AI read-only opsional berada pada R2; AI/forecast lanjutan pada R3. Evaluasi AI hanya wajib ketika fitur AI benar-benar diaktifkan.

## 2. Tanggal usaha dan kewajiban review

**PROPOSED DEFAULT:** `business_date` menunjuk hari operasional resto. `outlet_timezone` dan `business_day_cutoff` wajib dikonfigurasi serta disetujui sebelum live. Zona antarmuka pengguna tidak menentukan deadline. Contoh Asia/Jakarta dalam dokumen ini adalah data simulasi, bukan keputusan untuk seluruh resto.

Label `business_date=H` adalah tanggal kalender ketika interval hari usaha dimulai: `[H pada cutoff, H+1 pada cutoff)`. Deadline review tetap H+1 pukul 12.00 lokal, yaitu hari kalender setelah label H. Cutoff ≥12.00 tidak valid untuk profil H+1 ini karena hari usaha belum berakhir sebelum deadline; aktivasi ditolak sampai profil diselesaikan. Contoh cutoff 04.00: H=1 Nov mencakup 1 Nov 04.00 sampai sebelum 2 Nov 04.00, dan review jatuh tempo sebelum 2 Nov 12.00.

| Field | Aturan |
|---|---|
| `obligation_id` | Identitas stabil; unique `(tenant_id, resto_id, business_date, review_type)` |
| `business_date` | Hari H yang diperiksa; disimpan terpisah dari waktu pengiriman data |
| `deadline_at` | Instant UTC untuk H+1 pukul 12.00 zona resto; tepat waktu harus `< deadline_at` |
| `timezone_snapshot` | Zona yang digunakan saat kewajiban dibentuk; tidak berubah saat pengguna bepergian |
| `original_owner_id` | Snapshot SPV yang bertanggung jawab pada akhir H |
| `current_assignee_id` | Penerima tugas saat ini; perubahan harus melalui transfer/delegasi tercatat |
| `original_acm_id` | ACM pada snapshot tanggung jawab; pemeriksa pengganti harus berwenang |
| `calendar_version` | Kalender aktif/tutup/nonaktif yang digunakan |
| `assignment_history` | Penugasan, alasan, pemberi persetujuan, waktu berlaku |

Pembentukan kewajiban menggunakan upsert idempotent. Job yang dijalankan ulang tidak menambah kewajiban kedua. Bila assignment belum ada, kewajiban tetap dibuat sebagai `UNASSIGNED` dan dieskalasikan; tidak hilang dari denominator.

Kalender menyimpan `ACTIVE_OPEN`, `ACTIVE_TEMPORARILY_CLOSED`, `NOT_YET_OPEN`, atau `PERMANENTLY_CLOSED` beserta tanggal berlaku dan persetujuan. Dua status aktif tetap membutuhkan review. Tutup sementara wajib memiliki alasan dan bukti; transaksi nol yang lengkap berbeda dari transaksi belum masuk. Hari sebelum aktivasi atau setelah nonaktif permanen tidak membentuk kewajiban baru.

`active_from` dan `active_until` adalah label tanggal usaha inklusif: hari terakhir aktif tetap termasuk kewajiban dan denominator. Status permanently closed mulai pada hari berikutnya; jangan menafsirkan tanggal terakhir aktif sebagai hari pertama yang dikecualikan.

Transfer tugas tidak menulis ulang pemilik awal. Pengguna yang sudah keluar tidak mempertahankan hak akses hanya karena namanya ada dalam histori. Hak membaca/bertindak mengikuti grant terkini dan scope yang berlaku.

**BUSINESS GATE:** zona dan cutoff per lokasi, proses pengganti/cuti, serta penanggung jawab kewajiban tanpa assignment harus disahkan sebelum aktivasi review produksi.

## 3. Status review dipisahkan

Status tidak disatukan menjadi satu label “selesai”.

| Dimensi | Nilai | Perubahan |
|---|---|---|
| `workflow_status` | `NOT_STARTED`, `DRAFT`, `SUBMITTED`, `CHANGES_REQUESTED`, `ACCEPTED`, `CLOSED` | Melalui command berizin |
| `timeliness_status` | `NOT_SUBMITTED`, `ON_TIME`, `LATE` | Diturunkan dari penerimaan server pertama yang valid dibanding deadline |
| `data_quality_status` | `COMPLETE`, `INCOMPLETE`, `UNDER_RECONCILIATION` | Menunjukkan kondisi data pada snapshot versi review |
| `acm_disposition` | `PENDING`, `CHANGES_REQUESTED`, `ACCEPTED` | Ditautkan ke versi review yang diperiksa |
| `actual_change_status` | `UNCHANGED`, `CHANGED_AFTER_REVIEW`, `REVIEWED_NEW_VERSION` | Dibentuk saat angka sumber direvisi |

`first_submitted_at` hanya diset pada submission valid pertama dan tidak dapat diedit. Draft yang tersimpan sebelum 12.00 tidak sama dengan submission. Waktu klien atau timestamp lampiran tidak dapat dipakai memundurkan submission. Revisi setelah deadline tidak mengubah status ketepatan submission awal, tetapi memiliki timestamp dan histori tersendiri.

Setiap versi review mengacu pada `target_version`, `metric_definition_version`, `actual_snapshot_id`, dan data pendukung. Snapshot tidak berubah setelah submission. Actual baru membuat snapshot baru dan flag perubahan; tidak mengganti angka yang dahulu dibaca SPV.

Nama field di tabel merupakan nama kanonik yang sama dengan kontrak teknis. Pengiriman ulang kembali ke state `SUBMITTED` dengan nomor versi lebih tinggi; tampilkan label “dikirim ulang” dari histori, bukan enum tambahan yang maknanya sama.

Kartu KPI resmi mengikuti basis `posting_date` sesuai lampiran finance. Tampilan kejadian operasional menggunakan `occurred_at` dan `business_date` asal serta label yang berbeda. Late event periode tertutup diposting pada periode terbuka yang disahkan, kecuali reopen disetujui. Jangan memasukkan ulang event yang sama ke kedua basis pada kartu KPI yang sama. Snapshot review menyimpan `basis`, versi dan flag late booking beserta tautan ke transaksi asal. Koreksi tidak memindahkan obligation hari H atau mengubah pemilik/deadline historis; perbedaan tampilan operasional dan finansial dijelaskan melalui rekonsiliasi.

## 4. Kontrak command review

Nama command dalam tabel sama dengan kontrak teknis. `SubmitReview` menangani pengiriman pertama dan ulang dengan guard berbeda. URI HTTP final mengikuti OpenAPI per ticket; tidak boleh menciptakan perilaku atau state kedua untuk aksi yang sama.

| Command | Aktor dan prasyarat | Input wajib | Hasil dan penolakan |
|---|---|---|---|
| `SaveReviewDraft` | SPV/pengganti yang berwenang pada kewajiban | Obligation, expected version, catatan | Menyimpan draft; konflik versi ditolak agar tidak menimpa kerja lain |
| `SaveReviewRevision` | Assignee berwenang; CHANGES_REQUESTED | Expected version, catatan/perbaikan draft | Simpan revisi tanpa mengubah first submission atau menyatakan perbaikan telah diterima |
| `SubmitReview` | Assignee berwenang; draft lolos validasi | Snapshot KPI, kondisi data, temuan/hasil, tindakan atau justifikasi tidak perlu tindakan | Set timestamp server; `SUBMITTED`; tidak menghapus ketidaklengkapan data |
| `RequestReviewRevision` | ACM/pengganti berwenang; versi telah disampaikan | Versi yang diperiksa, alasan, bagian yang perlu diperbaiki | `CHANGES_REQUESTED`; timestamp awal dipertahankan |
| `SubmitReview` | Assignee berwenang; ada permintaan perbaikan | Versi baru, jawaban atas temuan | State kanonik `SUBMITTED`, label resubmitted dan versi baru; ACM harus memeriksa ulang |
| `AcceptReview` | ACM berwenang, tidak sekaligus menjadi penyampai versi itu | Versi, catatan pemeriksaan | `ACCEPTED`; konflik kepentingan membutuhkan checker lain |
| `CloseReview` | Sistem setelah penerimaan dan semua metadata wajib lengkap | Referensi versi accepted | Menutup review; tindakan terbuka tetap dilacak terpisah |
| `ReassignObligation` | Pejabat operasional dengan scope terkait | Assignee baru, alasan, efektif, otorisasi | Update penugasan kini; original owner dan histori tetap |
| `ReopenReviewForDataChange` | Service berizin atau ACM dengan scope; snapshot berubah | Versi review lama, snapshot baru, perubahan | ACCEPTED/CLOSED → CHANGES_REQUESTED; disposisi versi baru PENDING; snapshot dan acceptance lama tetap; first submit tidak berubah |

Review dengan data belum lengkap boleh dikirim sebelum deadline. Kelengkapan, kualitas, dan ketepatan waktu dilaporkan terpisah. Menerima review tidak menyatakan semua masalah resto telah selesai. Menutup review juga tidak menutup tindakan secara otomatis.

Jika koreksi actual mengubah angka setelah review, SPV menerima kebutuhan pemeriksaan ulang versi angka tersebut. Default: perubahan numerik atau kualitas data memicu flag; tidak memakai ambang materialitas tersembunyi. Versi yang diperiksa ulang direkam tanpa memundurkan waktu review awal.

Jika review masih draft, pengguna ditawari snapshot baru dan harus mengonfirmasi pembaruannya sebelum submit. Jika sudah SUBMITTED, ACM meminta revisi ke snapshot terbaru; jika sudah ACCEPTED/CLOSED, gunakan `ReopenReviewForDataChange`. Update snapshot tidak otomatis berarti review baru sudah disampaikan atau diterima. Event perubahan sama diproses idempotent.

## 5. Pemeriksaan ACM

**PROPOSED DEFAULT:** ACM menggunakan bundle `SPV × business_date` yang memuat seluruh kewajiban resto milik SPV pada snapshot hari H. Bundle memudahkan pekerjaan, sementara acceptance tetap per resto dan per versi review.

- Bundle tidak selesai hanya karena ACM membuka halaman atau mengklik ringkasan.
- Setiap resto harus memiliki disposisi; review yang belum disampaikan tetap muncul.
- Bila ada review diminta perbaikan atau belum diterima, bundle berstatus `INCOMPLETE`.
- Transfer tugas atau organisasi ditampilkan tanpa menghilangkan keterlacakan bundle asli.
- Status `COMPLETED` menyatakan semua versi wajib telah diterima; tindakan lanjutan dapat tetap terbuka.
- Sampling langsung adalah pekerjaan tambahan; tidak menggantikan pemeriksaan review SPV.
- Tenggat ACM dan SLA perbaikan adalah **BUSINESS GATE**. Sampai ditetapkan, sistem boleh menunjukkan pending age tetapi tidak melabeli ACM “terlambat” berdasarkan tenggat rekaan.

## 6. Intensitas review dan prioritas kerja

Kesehatan bulanan berbeda dari prioritas operasional hari ini. Resto sehat tetap dapat memiliki insiden urgent.

| Prioritas usulan | Pemicu default draft | Isi review |
|---|---|---|
| `NORMAL` | Tidak ada pemicu attention/urgent pada data yang lengkap | Konfirmasi KPI, kondisi, dan tindak lanjut terbuka |
| `ATTENTION` | Target/KPI terkonfirmasi tidak memenuhi, data tidak lengkap, tindakan lewat tenggat, atau kesehatan belum memenuhi | Diagnosis berbukti atau rencana pemeriksaan; PIC, tenggat, tindakan/justifikasi |
| `URGENT` | Insiden yang diklasifikasikan urgent oleh SOP keselamatan pangan/keuangan yang disahkan | Penanganan segera dan eskalasi menurut SOP; tidak menunggu H+1 |

Tidak ada angka keparahan baru yang dianggap disetujui. Ambang tren beberapa hari, materialitas uang, kategori insiden, penerima eskalasi, dan jam tenang adalah konfigurasi berversi yang memerlukan pengesahan. Salah satu KPI gagal dapat memicu attention; skor komposit tidak boleh menutupi kegagalan KPI.

## 7. Target harian dan bulanan

**PROPOSED DEFAULT:** target harian yang disetujui menjadi sumber pencapaian harian. Rencana bulanan digunakan untuk membuat draft harian; sistem tidak menebak target saat belum disetujui.

Target menyimpan outlet, tanggal, KPI, nilai, unit, mata uang, versi, status, approver, dan timestamp persetujuan. Tidak boleh ada dua versi approved aktif untuk outlet–tanggal–KPI yang sama. Perubahan dilakukan sebagai versi baru dengan alasan. Laporan “saat review” dan “terbaru” dibedakan.

Pembagian target bulanan draft:

1. Tetapkan hari eligible dan bobot setiap tanggal. Bobot sama merupakan pilihan draft; bukan kebijakan akhir pekan yang sudah disetujui.
2. `raw_i = monthly_target × weight_i / sum(weights)` memakai presisi desimal.
3. Bulatkan ke bawah sampai unit rupiah; distribusikan sisa rupiah satu per satu menurut pecahan terbesar.
4. Jika pecahan sama, tanggal lebih awal mendapat alokasi lebih dahulu.
5. Total target harian wajib sama persis dengan target bulanan. Bobot negatif atau total bobot nol ditolak.
6. CEO menyetujui versi final sebelum digunakan untuk evaluasi.

Target nol dapat dipakai untuk hari tutup sesuai kebijakan, tetapi rasio pencapaian ditampilkan `N/A`; target kosong ditampilkan `TARGET_NOT_SET`. Keduanya tidak diperlakukan sebagai target positif yang gagal dicapai.

Revisi berlaku surut secara default ditolak. Pengecualian memerlukan command khusus, alasan dan otorisasi; snapshot review lama tidak berubah. Data tercatat dengan versi KPI dan target yang digunakan pada waktu itu.

## 8. Kesehatan resto bulanan

Rumus rinci omzet, refund, TC, APC, COGS, dan NPM mengikuti lampiran KPI dan Akuntansi. Lampiran ini tidak membuat definisi keuangan kedua.

**CONFIRMED:** sehat bila rata-rata omzet harian bulanan >Rp3.000.000 dan NPM bulanan ≥10%.

**PROPOSED DEFAULT denominator:** hari kalender ketika resto berstatus aktif dalam bulan tersebut, termasuk tutup sementara. Outlet baru/tutup permanen di tengah bulan mendapat label `PARTIAL_MONTH`. Aturan ini harus disetujui bisnis sebelum digunakan pada status kesehatan resmi.

Hari tanpa transaksi yang datanya lengkap mempunyai omzet nol. Hari yang belum mengirim seluruh transaksi tidak boleh dianggap nol atau dikeluarkan dari pembagi. Statusnya belum lengkap dan kesehatan final belum dapat ditentukan.

| Data | Status |
|---|---|
| Omzet/NPM bulan yang sama tidak lengkap | `UNKNOWN_INCOMPLETE` |
| Data lengkap, periode belum ditutup | `PROVISIONAL`; nilai indikatif ditampilkan dengan label sementara |
| Final, omzet rata-rata >3 juta dan NPM ≥10% | `HEALTHY` |
| Final, hanya omzet tidak memenuhi | `UNHEALTHY_REVENUE` |
| Final, hanya NPM tidak memenuhi | `UNHEALTHY_PROFIT` |
| Final, keduanya tidak memenuhi | `UNHEALTHY_BOTH` |
| Penyebut NPM nol/tidak valid menurut kebijakan KPI | `NOT_ASSESSABLE`; alasan eksplisit |

Portofolio menampilkan jumlah resto eligible, berdata final, sehat, belum sehat, dan belum dapat dinilai. Rasio “sehat dari resto yang dinilai” menggunakan denominator final-assessable; jangan diberi label sebagai seluruh jaringan. Resto parsial tetap dapat dinilai setelah final tetapi ditandai dan dapat difilter; perbandingan same-store memakai cohort tersendiri.

## 9. Sampling ACM dasar — R1

Frekuensi **dua resto unik per ACM per minggu** adalah usulan yang belum disetujui. Minggu draft Senin 00.00 sampai Senin berikutnya, menggunakan timezone yang disahkan untuk area ACM.

- Satu resto dipilih berdasarkan risiko; satu berdasarkan rotasi. Pilihan kedua harus berbeda.
- Kunjungan kedua ke resto yang sama menambah jumlah kunjungan, bukan jumlah resto unik.
- Simpan alasan pemilihan, metode risiko/rotasi/manual, jadwal, actual visit, bukti, temuan, dan tindakan.
- Hitung cakupan resto unik dan usia kunjungan terakhir; tidak mengklaim seluruh area sudah tercakup hanya dari jumlah kunjungan.
- Override pilihan, pembatalan, dan penggantian lokasi memerlukan alasan; kunjungan batal tidak dihitung completed.
- Pelaporan rotasi lintas periode tersedia secara dasar. Optimasi rute dan penilaian risiko lanjutan merupakan R2.

## 10. Tindakan dan pengukuran ketepatan waktu

Status: `OPEN → IN_PROGRESS → PENDING_VERIFICATION → VERIFIED_CLOSED`. Cabang `BLOCKED`, `CHANGES_REQUESTED`, `REOPENED`, `CANCELLED` menyimpan alasan dan histori. Satu PIC utama dan satu verifikator berwenang; orang yang sama tidak mengesahkan pekerjaannya sendiri.

Waktu penting: `deadline_at`, `submitted_for_verification_at`, `verified_at`, dan `verification_due_at` jika SLA verifikasi sudah ditetapkan. Pengukuran dibedakan:

- **PIC:** submission bukti valid yang akhirnya diterima dibanding deadline pekerjaan. Submission ditolak karena pekerjaan belum selesai tidak membekukan ketepatan waktu palsu.
- **Verifikator:** waktu pemeriksaan dibanding SLA verifikasi; selama SLA belum disahkan tampilkan durasi pending, bukan breach rekaan.
- **Hasil:** perubahan KPI/hasil yang diharapkan, yang dapat diketahui setelah tugas selesai.

Pembatalan membutuhkan alasan dan approval; tidak dianggap sukses. Pergantian tenggat menyimpan tanggal awal dan baru, alasan serta approver. Laporan dapat menunjukkan kepatuhan terhadap tenggat awal dan tenggat yang disetujui.

## 11. Hak akses operasional

Setiap command mengecek user aktif, permission action, scope lokasi/organisasi, dan versi record di server. Menu tersembunyi bukan kontrol akses. `view`, `create`, `submit`, `approve`, `transfer`, dan `export` adalah permission terpisah.

| Peran | Scope draft | Batas |
|---|---|---|
| SPV | Resto yang ditugaskan saat ini dan histori yang secara eksplisit diizinkan | Tidak menyetujui review sendiri sebagai ACM |
| ACM | SPV/resto dalam grant saat ini | Tidak menerima review yang dirinya sampaikan sebagai pengganti |
| Manajer | Area dalam grant | Override memerlukan permission dan alasan |
| CEO | Scope korporat yang diberikan | Akses data HR/owner sensitif tetap eksplisit |
| PIC resto | Resto sendiri | Tidak otomatis boleh membaca detail gaji, saham, atau rekening |
| Admin sistem | Konfigurasi akun sesuai mandat | Tidak otomatis menjadi approver bisnis |

Grant berakhir tidak memberikan akses melalui tautan lama, ekspor, notifikasi, atau API. Catatan historis tetap menyimpan nama/ID pelaku untuk audit sesuai akses pembaca saat ini.

## 12. Skenario penerimaan operasional

Angka berikut adalah data simulasi, bukan data PT EBM. Waktu Asia/Jakarta dipakai hanya sebagai fixture pengujian.

| ID | Rilis | Given / When | Then |
|---|---|---|---|
| O01 | R1 | H=1 Nov; review diterima server 2 Nov 11:59:59.999 | Tepat waktu |
| O02 | R1 | Review diterima tepat 12:00:00.000 | Terlambat karena ketentuan sebelum 12 |
| O03 | R1 | Draft disimpan 11:40, submit 12:05 | Terlambat; save draft tidak dihitung submit |
| O04 | R1 | Klien menyatakan 11:50, server menerima 12:03 | Terlambat; waktu klien tidak dapat memundurkan submission |
| O05 | R1 | Job membentuk kewajiban hari yang sama tiga kali | Hanya satu obligation per resto–hari–jenis |
| O06 | R1 | Resto aktif tutup renovasi satu hari | Review tetap wajib; nol hanya jika transaksi lengkap; bukti penutupan tersimpan |
| O07 | R1 | Resto baru aktif 10 Nov | Tidak ada kewajiban sebelum 10 Nov; bulan diberi label parsial |
| O08 | R1 | SPV A bertanggung jawab akhir H, B menggantikan H+1 | A tersimpan sebagai owner awal; transfer ke B eksplisit; tidak ada obligation ganda |
| O09 | R1 | Akun A dicabut setelah transfer | Histori tetap menyebut A; A tidak dapat membuka record dengan URL lama |
| O10 | R1 | SPV submit 11:45 dengan data POS belum lengkap | Tepat waktu + data belum lengkap; bukan review lengkap |
| O11 | R1 | ACM meminta perbaikan 13:00, SPV resubmit 14:00 | Timestamp awal tetap 11:45; revisi dan hasil pemeriksaan tercatat |
| O12 | R1 | Actual berubah setelah review diterima | Snapshot lama tetap; flag `CHANGED_AFTER_REVIEW`; versi baru perlu diperiksa |
| O13 | R1 | Lima resto dalam bundle, empat accepted, satu pending | Bundle belum completed |
| O14 | R1 | ACM menyelesaikan sampling tetapi dua review SPV belum diperiksa | Sampling tidak menutup kewajiban review |
| O15 | R1 | Tenggat ACM belum disahkan | Tampilkan pending age; jangan label late dengan nilai default tersembunyi |
| O16 | R1 | Target Rp100.000 dibagi tiga hari berbobot sama | Rp33.334, Rp33.333, Rp33.333 urut tanggal; total Rp100.000 |
| O17 | R1 | Seluruh bobot nol atau satu bobot negatif | Alokasi ditolak dengan pesan yang menjelaskan kesalahan |
| O18 | R1 | Target belum diset, actual Rp3,5 juta | Pencapaian `TARGET_NOT_SET`, bukan 0% atau gagal |
| O19 | R1 | Target Rp4 juta, actual Rp3,5 juta | Pencapaian 87,5%; terpisah dari status kesehatan bulanan |
| O20 | R1 | Revisi target setelah review | Review lama tetap merujuk target lama; laporan terbaru diberi versi baru |
| O21 | R1 | 30 hari aktif, omzet bersih Rp90 juta, NPM 10%, final | Rata-rata Rp3 juta tepat; belum sehat karena omzet |
| O22 | R1 | 30 hari aktif, omzet bersih Rp93 juta, NPM 10%, final | Rp3,1 juta/hari; sehat |
| O23 | R1 | Satu dari 30 hari belum sinkron | Tidak membagi hanya 29 hari; kesehatan final belum dapat dinilai |
| O24 | R1 | NPM bulan Oktober tersedia, omzet yang ditinjau November | Tidak menggabungkan keduanya menjadi status sehat November |
| O25 | R1 | 220 eligible, 200 final-assessable, 120 sehat | Tampilkan 120/200 dinilai sehat dan 20 belum dapat dinilai; bukan 60% seluruh jaringan |
| O26 | R1 | ACM kunjungi resto X dua kali dalam minggu sama | Dua kunjungan, satu resto unik; target dua resto belum terpenuhi bila kebijakan diaktifkan |
| O27 | R1 | PIC submit bukti 10:00 sebelum due 12:00, diterima verifikator esok hari | PIC tepat waktu; waktu verifikasi diukur terpisah |
| O28 | R1 | Bukti PIC sebelum deadline ditolak karena belum selesai; bukti valid esok hari | Pelaksanaan tidak dianggap tepat waktu dari submission yang ditolak |
| O29 | R1 | Tindakan dibatalkan dengan otorisasi | Dilaporkan cancelled, tidak dihitung sukses |
| O30 | R1 | Pengguna merangkap SPV dan ACM pada review yang sama | Dilarang menerima submission sendiri; perlu checker lain |
| O31 | R1 | User mengganti resto_id pada request di luar grant | Server menolak, termasuk ekspor dan akses lampiran |
| O32 | R1 | Resto sehat bulanan mengalami insiden urgent yang sah | Prioritas urgent; status kesehatan historis tidak ditimpa |
| O33 | R2 | Semua tugas inisiatif selesai tetapi nilai KR belum mencapai target | OKR tidak otomatis 100% |
| O34 | R2 | Modul bagi hasil belum diaktifkan pada pilot R1 | UAT distribusi laba tetap deferred, tidak diklaim lulus dan tidak memblokir R1 |
| O35 | R2/R3 saat aktivasi AI | AI belum tersedia di R1 | Pengujian AI belum berlaku; pengujian akses aplikasi R1 tetap wajib |
| O36 | R1 | Profil cutoff 04.00; transaksi 2 Nov 02.00, cutoff berikutnya 2 Nov 04.00 | Label hari usaha 1 Nov; obligation H+1 due sebelum 2 Nov 12.00 |
| O37 | R1 | Profil cutoff 12.00 atau 15.00 untuk H+1 sebelum noon | Konfigurasi ditolak; tidak menghasilkan deadline sebelum hari usaha selesai |
| O38 | R1 | active_until=15 Nov, permanently closed mulai 16 Nov | Review H=15 Nov tetap wajib pada 16 Nov; hari usaha 16 Nov tidak menambah obligation |
| O39 | R1 | Late sale H tiba setelah period close dan disetujui sebagai adjustment periode terbuka | KPI resmi mengikuti posting_date; operasional menunjukkan hari asal; obligation H tidak dipindah; rekonsiliasi menjelaskan perbedaan |

## 13. Syarat siap coding per fitur

Satu fitur baru boleh dinyatakan `READY_FOR_IMPLEMENTATION` setelah actor/scope, trigger, input, state transition, validasi, dampak data, exception, audit, dan skenario UAT terkait jelas. Kebijakan terbuka dicatat sebagai gate spesifik; tidak diterjemahkan developer menjadi keputusan bisnis diam-diam.

Untuk production activation, zona/cutoff, kalender, pemilik, target, rumus KPI, approval, dan tenggat yang dipakai harus memiliki versi kebijakan yang disetujui. Nilai simulasi tidak boleh menjadi konfigurasi produksi otomatis.

Gate lintas rilis mengikuti matriks rilis: R1 tidak menunggu fitur R2/R3 yang disabled, tetapi tetap memerlukan seluruh dependency yang dibutuhkan alur R1. Penyelesaian dokumen bukan bukti pengujian sudah dijalankan.
