# Login dan hak akses lokal EBM

Pembaruan: [POS offline kini terhubung login](POS-OFFLINE.md). Panduan ini menggantikan keterangan lama tentang POS offline yang belum terhubung. Gunakan alamat terbaru http://127.0.0.1:8085 pada sesi ini.

## Integrasi kasir dengan dashboard

Versi integrasi yang aktif pada sesi perbaikan menggunakan http://127.0.0.1:8083. Pilih tanggal bisnis yang sama pada Kasir, Ringkasan dan Review SPV. Saat membuka menu Ringkasan/Review, data dibaca ulang dari database lokal. Data awal contoh hanya berlaku 31 Oktober 2026; tanggal lain dimulai dari nol. Transaksi yang dibuat versi sebelumnya tanpa tanggal bisnis dimasukkan ke tanggal contoh tersebut tanpa mengubah bukti timestamp aslinya.

Omset = data awal contoh + nominal transaksi tunai tersimpan pada outlet/tanggal itu. TC = TC awal + jumlah struk, bukan jumlah paket. APC = omset/TC; jika TC nol ditampilkan nol. COGS belum dihitung dari transaksi karena modul inventory dan biaya aktual belum tersedia. Status LOCAL_PENDING berarti belum diterima cloud, tetapi transaksi sudah masuk proyeksi operasional lokal. Pembacaan dashboard berulang tidak menambahkan transaksi kembali. Tidak ada auto-refresh lintas tab; buka ulang menu atau muat ulang halaman untuk mengambil data terbaru.

Delapan tes integrasi server lulus termasuk pertambahan omset/TC, isolasi tanggal/outlet, pembacaan ulang tanpa penggandaan dan validasi tanggal.

Buka http://127.0.0.1:8082 pada sesi ini. Untuk menjalankan ulang, klik `Mulai-Simulasi-EBM.cmd` lewat File Explorer dan gunakan alamat yang ditampilkan. Jangan memakai `python -m http.server`; API login memerlukan `app/server.py`.

Kata sandi awal semua akun: **EbmDemo!2026**.

| Username | Akses awal |
| --- | --- |
| admin | Semua fitur contoh, pengguna dan audit |
| ceo, mgr | Dashboard seluruh outlet contoh dan baca review |
| acm | Dashboard dan baca review outlet A–B |
| spv | Dashboard dan tulis review outlet A–B |
| kasir | Kasir dan transaksi lokal outlet A |
| finance | Dashboard dan transaksi lokal seluruh outlet contoh |
| gudang | Peta modul; inventory belum tersedia |

Semua akun dapat membuka Akun saya, mengganti kata sandi dan keluar. Cakupan ini merupakan profil simulasi. Menu serta API server memeriksa izin.

## Cara mencoba

1. Masuk sebagai kasir: tidak ada menu Review/Pengguna, hanya outlet A.
2. Keluar dan masuk sebagai SPV: review dapat ditulis untuk A–B.
3. Masuk sebagai CEO: review hanya dapat dilihat.
4. Masuk sebagai admin, pilih Pengguna & akses. Ubah peran/cakupan/status akun kemudian simpan. Sesi lama akun tersebut dicabut; masuk ulang untuk melihat hasilnya. Administrator dapat mengaktifkan kembali akun yang dinonaktifkan. Akun admin sendiri dilindungi dari perubahan akses di halaman ini.
5. Klik nama akun untuk melihat izin atau mengganti kata sandi. Perubahan kata sandi mencabut seluruh sesi akun tersebut.

## Sesi dan data

Lima kegagalan login memblokir sementara 15 menit. Sesi idle 30 menit atau umur 12 jam memerlukan login ulang. Hash scrypt, cookie HttpOnly/SameSite=Strict, CSRF, pengecekan origin dan audit tersedia. HTTPS/cookie Secure, MFA, pemulihan sandi, pembuatan akun dan persetujuan akses produksi belum tersedia. Akun demo tidak boleh dipakai untuk data produksi.

Akun, sesi, audit, transaksi dan review baru tersimpan di `.runtime/ebm.sqlite3`, di luar direktori file web dan dikecualikan dari Git. Perubahan akun bertahan setelah server restart. Server hanya mendengarkan loopback komputer ini.

Data IndexedDB lama tetap berada di browser dan belum dimigrasi. Laboratorium ekspor/impor lama tidak ditampilkan pada versi login agar tidak menjadi jalan melewati scope. Transaksi/review sekarang memakai server lokal aktif dan tidak membutuhkan internet. POS offline mandiri, Android native, cloud dan modul ERP lain belum tersedia.

## Pengujian

Tujuh tes integrasi HTTP lulus: wajib login/file privat, scope kasir/CSRF, SPV vs CEO, pencabutan akses/logout, perubahan sandi, lockout, expiry. Tes memakai database sementara. Perintah: `python -m unittest discover -s app -p test_auth.py`. Login kasir dan menu berizin diperiksa langsung di browser; sintaks JavaScript juga lulus.
