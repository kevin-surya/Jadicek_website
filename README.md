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

## Deploy ke Vercel

Folder ini sudah memiliki `api/predict.py`, `vercel.json`, `.python-version`, dan dependensi runtime yang dipatok. Model `.joblib` di `models/` ikut masuk ke bundle Python Function. Training dilakukan secara lokal; Vercel hanya memuat artefak dan menjalankan inferensi.

### Melalui GitHub

1. Jadikan folder `jadicek-redesign` sebagai root repository, atau pilih folder tersebut sebagai **Root Directory** ketika mengimpor monorepo di Vercel.
2. Push seluruh isi folder, termasuk `models/*.joblib`.
3. Di Vercel pilih **Add New → Project**, impor repository, lalu pastikan **Framework Preset = Other**.
4. Biarkan Build Command dan Output Directory kosong, kemudian deploy.
5. Buka `https://domain-anda.vercel.app/api/predict`. Respons `status: ready` berarti model berhasil dimuat.
6. Uji formulir pada halaman utama. Frontend sudah memakai URL relatif `/api/predict`, sehingga tidak memerlukan environment variable.

### Melalui Vercel CLI

```powershell
cd jadicek-redesign
npx vercel
npx vercel --prod
```

Jawab root project dengan folder saat ini dan framework dengan **Other**. Perintah pertama membuat Preview Deployment; setelah diuji, perintah kedua menerbitkan Production Deployment.

Python Function memiliki cold start karena perlu memuat pandas, scikit-learn, LightGBM, dan dua model. Jika build melaporkan function terlalu besar, aktifkan Fluid Compute dan tambahkan environment variable `VERCEL_SUPPORT_LARGE_FUNCTIONS=1`, lalu redeploy. Jangan mengunggah CSV training atau notebook ke function; keduanya tidak dibutuhkan saat prediksi.

## Upload ke Hugging Face

Tersedia dua folder siap unggah:

- `huggingface-model/`: repository Model Hub untuk penyimpanan dan versioning artefak.
- `huggingface-space/`: Docker Space FastAPI yang menjalankan model sebagai API.

Pasang CLI dan login tanpa menaruh token di source code:

```powershell
python -m pip install -U huggingface_hub
hf auth login
```

Buat model repository bernama `jadicek-model` melalui `https://huggingface.co/new`, lalu unggah:

```powershell
hf upload USERNAME/jadicek-model ./huggingface-model . --repo-type model
```

Buat Space bernama `jadicek-api` melalui `https://huggingface.co/new-space` dengan SDK **Docker**, lalu unggah:

```powershell
hf upload USERNAME/jadicek-api ./huggingface-space . --repo-type space
```

Setelah status Space **Running**, tes:

```text
https://USERNAME-jadicek-api.hf.space/health
```

### Alternatif gratis tanpa compute Space

Static Space tidak dapat menjalankan Python. Untuk akun gratis, simpan model di Model Hub lalu biarkan Vercel Python Function menjalankan inferensi. Di **Vercel → Project Settings → Environment Variables**, tambahkan:

```text
HF_MODEL_REPO=USERNAME/jadicek-model
HF_MODEL_REVISION=main
```

Untuk model repository public, tidak diperlukan token. Untuk repository private, tambahkan `HF_TOKEN` sebagai secret Vercel menggunakan token Hugging Face bertipe **Read**. Jangan memasukkan token ke `config.js`.

Biarkan konfigurasi frontend tetap kosong agar browser memanggil Vercel:

```js
window.JADICEK_API_URL = "";
```

Kemudian redeploy Vercel. Pada cold start, function mengunduh hanya dua file `.joblib` dari Hub dan menyimpannya pada cache sementara. Untuk deployment yang stabil, ganti `HF_MODEL_REVISION` dengan commit hash Model Hub setelah model final.

Pipeline LightGBM tetap melakukan inferensi di CPU. Namun, akun gratis yang hanya
dapat memakai hardware ZeroGPU mengharuskan fungsi Gradio terdaftar memakai dekorator
`@spaces.GPU`. Karena prediksi setelah model dimuat berlangsung sangat singkat,
`predict` memakai `@spaces.GPU(duration=1)` agar reservasi kuota per request minimal.
Jika kuota ZeroGPU pengguna sudah habis, request tetap ditolak sampai kuota direset.

Jika Space digunakan, isi `window.JADICEK_GRADIO_URL` di `config.js` dengan alamat
`https://USERNAME-jadicek-api.hf.space`. Frontend memanggil endpoint Gradio
`/gradio_api/call/predict` secara langsung tanpa dependensi JavaScript eksternal.
