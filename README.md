# Jadicek — desain baru

Website mandiri dengan HTML, CSS, JavaScript, dan server Python bawaan. Folder `jadicek` serta notebook asli tidak diubah. Dependensi Python tercantum di `requirements.txt`.

## Menjalankan

Di PowerShell dari folder `web`:

```powershell
cd jadicek-redesign
python server.py
```

Buka **http://localhost:3000**. Hentikan dengan Ctrl+C. Jika port digunakan, atur `$env:PORT='3001'` sebelum menjalankan.

## Fitur

- Desain teal dan krem dengan ilustrasi jantung berbasis CSS/SVG, tanpa aset atau font eksternal.
- Navigasi mobile, panduan, FAQ, dan formulir tiga tahap dengan validasi.
- Seluruh masukan profil yang digunakan website lama, perhitungan BMI, ringkasan, pengubahan jawaban, reset, serta unduhan JSON.
- Tidak memakai localStorage, analytics, atau database.
- Pipeline model lokal untuk diabetes dan penyakit jantung; tidak membuat skor prediksi saat artefak model belum tersedia.

## Model dan training

Pipeline yang dapat direproduksi berada di `train_models.py`. Jalankan dari folder ini untuk melatih ulang model:

```powershell
python train_models.py --data "..\..\data_fix_satdat_2023.csv"
```

Hasil disimpan di `models/`:

- `diabetes_pipeline.joblib`: preprocessing dan LightGBM diabetes.
- `heart_pipeline.joblib`: preprocessing dan LightGBM jantung.
- `metrics.json`: sumber data, waktu training, jumlah baris, dan evaluasi holdout.

Server memuat kedua pipeline secara otomatis saat dimulai. Endpoint lokalnya adalah `POST /api/predict`.

Payload: `bmi` (angka); `umur` (kelompok umur `1.0`–`14.0`); `jenis_klmn` (`laki-laki`/`perempuan`); `domisili` (`1.0`/`2.0`); `merokok`, `alkohol`, `olahraga`, `tekanan_darah_tinggi`, `kolesterol_tinggi`, `susah_jalan` (`ya`/`tidak`); `kesehatan_umum` (`sangat_baik`/`baik`/`cukup`/`kurang`); `aktivitas_fisik` (`sangat_aktif`/`aktif`/`cukup`/`kurang`).

Pipeline mereproduksi urutan sel aktif di `satria_data - Copy.ipynb`, termasuk pemetaan label **0 = kondisi ada/riwayat, 1 = kondisi tidak ada/borderline**, pembuangan nilai kosong/7/9, dan one-hot encoding pada sel 38. Seperti sel 69 notebook, fitur diabetes pada model jantung menjadi konstan 0 setelah pemetaan kedua; perilaku ini dipertahankan agar hasil evaluasi dapat direproduksi.

Angka sekitar 84% dan 93% pada notebook adalah akurasi/recall tertimbang pada target yang tidak seimbang. Nilai itu bukan recall kelas penyakit. `metrics.json` mencatat metrik notebook dan metrik khusus kelas penyakit secara terpisah. Skor API adalah probabilitas keluaran model untuk kelas penyakit, bukan risiko klinis.

Server hanya mendengarkan localhost untuk pengembangan. Jika akan dipublikasikan, gunakan hosting HTTPS dan backend produksi yang sesuai. Input tidak disimpan oleh website; kebijakan penyimpanan API bergantung pada layanan yang Anda hubungkan.
