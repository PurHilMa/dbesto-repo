# ERP EBM d'Besto — simulasi lokal

Aplikasi web simulasi: login dan hak akses, dashboard KPI, review SPV, POS tunai offline, sinkronisasi idempoten dan asisten tanya-jawab berbasis aturan.

## Menjalankan

Memerlukan Python 3 dan browser modern. Tidak memerlukan paket Python tambahan.

```sh
python app/server.py
```

Buka alamat localhost yang ditampilkan. Di Windows pada komputer pengembangan, tersedia Mulai-Simulasi-EBM.cmd.

## Akun demo

Username: admin, ceo, mgr, acm, spv, kasir, finance, gudang. Kata sandi awal: EbmDemo!2026. Akun dan seluruh data adalah simulasi. Jangan mengekspos server ini ke internet atau menggunakan data produksi.

## Pengujian

```sh
python -m unittest discover -s app -p test_auth.py
```

## Dokumentasi

- [Login dan hak akses](app/LOGIN.md)
- [POS offline](app/POS-OFFLINE.md)
- [Asisten lokal](app/ASISTEN.md)
- [Perencanaan ERP](docs/README.md)

Database, sesi dan transaksi lokal dibuat pada .runtime/ dan tidak disertakan dalam repository. Mode offline dan izin 8 jam masih profil simulasi. Asisten belum menggunakan model generatif. Android native, cloud, inventory dan pembukuan belum tersedia.
