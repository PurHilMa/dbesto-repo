# EBM — simulasi web lokal

Pembaruan POS: [Panduan POS offline terhubung login](POS-OFFLINE.md). Versi aktif terbaru: http://127.0.0.1:8085. POS offline web kini tersedia untuk simulasi tunai; keterangan batas offline pada versi lama di bawah digantikan panduan ini.

Panduan terkini: [Login dan hak akses](LOGIN.md).

Fitur baru: [Asisten EBM lokal](ASISTEN.md), panel kanan bawah dengan jawaban berdasarkan data berizin. Versi aktif terbaru: http://127.0.0.1:8084. Mode ini berbasis aturan; AI generatif belum terhubung.

Klik dua kali `Mulai-Simulasi-EBM.cmd` lewat File Explorer Windows. Gunakan alamat yang dicetak peluncur. Server memakai port kosong mulai 8080. Pada sesi login terbaru, alamat aktif adalah http://127.0.0.1:8082.

Login memerlukan `app/server.py`; jangan memakai `python -m http.server`.

Fitur tersedia: login lokal, delapan profil peran demo, scope outlet, admin perubahan akses/status akun, audit, ganti kata sandi, dashboard fixture, draft review dan penjualan tunai di server lokal. Semua memakai data simulasi.

Akun, sesi dan transaksi baru tersimpan di `.runtime/ebm.sqlite3`. Server lokal harus aktif. Data IndexedDB lama tidak dihapus dan belum dimigrasi; laboratorium ekspor/impor lama tidak ditampilkan pada versi login. Android native, cloud, mode POS offline mandiri, inventory, pembukuan, marketing, OKR dan AI belum diimplementasikan.

Tujuh tes integrasi login/hak akses lulus. Lihat LOGIN.md untuk skenario mencoba dan batas kesiapan produksi.
