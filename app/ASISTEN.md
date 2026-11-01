# Asisten EBM lokal

Alamat versi pada sesi ini: http://127.0.0.1:8084. Setelah login, buka tombol Asisten AI di kanan bawah.

Versi ini adalah tanya-jawab berbasis aturan, belum model AI generatif. Tidak memanggil layanan eksternal atau membutuhkan API key. Mendukung ringkasan omset/TC/APC, pencapaian target, urutan outlet di bawah target, COGS contoh, draft review dan definisi KPI. Tidak dapat menjawab semua variasi pertanyaan bahasa alami atau seluruh kebutuhan analisis.

Data dibaca ulang di server untuk setiap pertanyaan. Izin dan scope memakai handler yang sama dengan dashboard. Tidak ada akses langsung ke password, sesi, konfigurasi rahasia atau database melalui asisten. Jawaban menampilkan tanggal bisnis dan sumber; angka belum tersedia dijelaskan sebagai belum tersedia. Asisten read-only dan tidak menjalankan instruksi dari isi review.

Tanggal mengikuti pilihan halaman; pertanyaan dapat menyebut satu tanggal ISO seperti 2026-10-31. Rentang/perbandingan tanggal dan percakapan lanjutan yang membutuhkan ingatan konteks belum didukung. Riwayat hanya ada pada tampilan dan dibersihkan saat akun/tanggal berganti. Pertanyaan tidak disimpan dalam audit; hanya aktivitas dan tanggalnya.

Contoh: “Berapa omset dan TC resto A?”, “Outlet mana di bawah target?”, “Review mana yang belum selesai?”, “Apa itu APC?”. Data contoh tetap dipisahkan dari laporan pembukuan final.

Sembilan tes integrasi lulus termasuk akses lintas outlet, penolakan review bagi kasir, data yang belum tersedia, autentikasi/CSRF dan jawaban yang berubah setelah transaksi baru. Tanya-jawab omset/TC juga diverifikasi di browser. Untuk percakapan AI generatif bebas diperlukan model lokal atau integrasi penyedia AI tersendiri; belum ada yang dikonfigurasi.
