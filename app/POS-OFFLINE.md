# POS tunai offline terhubung login

Versi aktif sesi ini: http://127.0.0.1:8085. Gunakan browser dan alamat yang sama; cache serta antrean perangkat terikat origin (termasuk port).

## Mencoba

1. Masuk sebagai `kasir` / `EbmDemo!2026` dengan tombol **Masuk online & siapkan POS**. Server harus hidup pada tahap pertama.
2. Login menyiapkan profil offline terenkripsi kata sandi, izin tunai 8 jam simulasi, identitas perangkat, daftar outlet berizin, harga contoh Rp30.000 dan cache halaman melalui service worker.
3. Di Kasir, centang **Uji offline (hentikan pengiriman POS)**, lalu simpan penjualan. Statusnya **Tersimpan perangkat**. Pada tahap ini belum masuk Ringkasan/Review SPV server.
4. Muat ulang halaman, isi akun yang sama, pilih **Buka POS offline**. Kata sandi membuka profil lokal tanpa login ke server. Antrean transaksi tetap ada. Hanya POS, antrean dan peta modul tersedia pada sesi offline.
5. Klik **Kembali ke login online**, masuk online sebagai akun yang sama. Klik **Sinkronkan ke server lokal**. Status sukses menjadi **Diterima server lokal** dan transaksi ikut omset/TC/APC Ringkasan serta Review SPV pada tanggal yang sama. Pengiriman juga dicoba saat menyimpan transaksi online, saat browser kembali online dan setiap 15 detik selama sesi online POS aktif.
6. Kirim ulang: ID event dan receipt server mencegah penggandaan omset/TC. ID yang sama dengan payload berbeda menjadi konflik, bukan ditimpa.

Untuk gangguan server sebenarnya, aplikasi yang sudah disiapkan dapat dibuka dari cache pada alamat yang sama dan profil dapat dibuka melalui tombol offline. Browser harus mendukung service worker, IndexedDB dan WebCrypto pada localhost. Belum ada APK Android atau uji printer/perangkat fisik Android. Uji browser yang dilakukan mencakup tombol simulasi offline, persistensi setelah reload, pembukaan profil dengan kata sandi, lalu sinkronisasi kembali; pengujian mematikan server/putus jaringan fisik belum dilakukan.

## Aturan akses dan status

Izin diikat username, ID perangkat dan outlet ketika server menerbitkannya. Saat menerima event server memeriksa token izin, identitas pengguna/perangkat, scope penerbitan dan scope terkini, peran POS, masa berlaku, tanggal serta nominal. Izin hanya untuk penjualan tunai biasa; tidak untuk refund, perubahan harga, approval atau administrasi akun.

- PENDING: tersimpan tahan reload pada perangkat, belum ada receipt server.
- RECEIVED: bukti dan efek operasional lokal tersimpan dalam transaksi database yang sama; belum posting pembukuan/cloud.
- EXCEPTION: bukti tersimpan di inbox server tetapi belum dihitung sebagai penjualan dashboard; misalnya akses dicabut, izin habis atau nilai tidak valid. Penyelesaian exception manual belum tersedia.
- CONFLICT: ID sudah ada dengan isi berbeda; bukti asal dipertahankan, antrean lokal tidak dihapus.

API sinkronisasi memerlukan login online pengguna pemilik bukti dan CSRF. Akun berbeda tidak dapat mengirim bukti orang lain; akses API tetap diperiksa server. Akun nonaktif atau sesi kedaluwarsa harus diselesaikan lewat login/admin; bukti tidak dibuang.

Logout online, perubahan sandi dan perubahan akses mencabut izin di server. Perangkat terputus tidak bisa menerima pencabutan seketika: pembukaan lokal masih mengikuti profil yang tersimpan sampai batas 8 jam, sedangkan pengiriman sesudah pencabutan menjadi exception. Logout lokal menghapus profil untuk pembukaan offline berikutnya, tetapi menyimpan antrean. Profil lama tidak diperbarui otomatis setelah kata sandi berubah; siapkan ulang melalui login online.

## Penyimpanan dan batas simulasi

IndexedDB `ebm-offline-pos-v1`: profil dienkripsi AES-GCM dengan kunci turunan PBKDF2 kata sandi; kata sandi plaintext tidak disimpan. Payload antrean dienkripsi dengan kunci nonextractable yang disimpan pada profil browser. Pemisahan username diterapkan pada UI dan server; ini bukan pengganti isolasi akun OS, attestation perangkat atau keamanan aplikasi Android produksi. Menghapus data browser dapat menghapus transaksi belum sinkron; jangan membersihkan data selama masih ada antrean.

Izin menggunakan token acak server yang hash-nya tersimpan; bukan sertifikat perangkat atau lease dengan verifikasi tanda tangan publik pada perangkat. Durasi 8 jam, harga tetap dan aturan clock drift merupakan profil simulasi, belum kebijakan produksi yang disahkan. Izin kedaluwarsa atau pengiriman terlambat dipertahankan sebagai exception.

Server menyimpan `offline_leases` dan `offline_inbox` dalam `.runtime/ebm.sqlite3`. Unique `(device,event_id)` dan penyimpanan receipt+records+audit atomik mencegah efek ganda bila respons hilang lalu browser retry. Receipt baru direspons setelah commit database. Dashboard server tidak memasukkan transaksi yang masih hanya ada di perangkat; belum ada indikator cakupan semua perangkat pada dashboard jaringan.

## Verifikasi

Sebelas pengujian integrasi HTTP lulus. Tambahan offline memeriksa izin hanya untuk peran POS, batas outlet, salah perangkat, replay idempoten, konflik payload, omset/TC hanya bertambah satu kali, izin kedaluwarsa, akses dicabut dan bukti exception tetap tersimpan. Sintaks JavaScript diperiksa. Browser berhasil menunjukkan transaksi tersimpan perangkat → tetap ada setelah reload/login offline → diterima server lokal.
