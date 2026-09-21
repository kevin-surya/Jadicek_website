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

Folder ini sudah memiliki `api/predict.py` sebagai proxy terautentikasi ke Hugging
Face Space. Model tetap dijalankan di Space; token Hugging Face tidak pernah dikirim
ke browser.

### Melalui GitHub

1. Jadikan folder `jadicek-redesign` sebagai root repository, atau pilih folder tersebut sebagai **Root Directory** ketika mengimpor monorepo di Vercel.
2. Push seluruh isi folder.
3. Di Vercel pilih **Add New → Project**, impor repository, lalu pastikan **Framework Preset = Other**.
4. Biarkan Build Command dan Output Directory kosong, kemudian deploy.
5. Di **Project Settings → Environment Variables**, tambahkan `HF_TOKEN` dengan
   token Hugging Face bertipe **Read** untuk Production, Preview, dan Development.
6. Redeploy, lalu buka `https://domain-anda.vercel.app/api/predict`. Respons
   `status: ready` dan `authenticated: true` berarti proxy siap.
7. Uji formulir pada halaman utama. Frontend memakai URL relatif `/api/predict`.

### Melalui Vercel CLI

```powershell
cd jadicek-redesign
npx vercel
npx vercel --prod
```

Jawab root project dengan folder saat ini dan framework dengan **Other**. Perintah pertama membuat Preview Deployment; setelah diuji, perintah kedua menerbitkan Production Deployment.

Python Function Vercel hanya meneruskan request dan menambahkan header
`Authorization: Bearer $HF_TOKEN`. Jangan memasukkan token ke `config.js`, `app.js`,
atau repository GitHub karena seluruh kode frontend dapat dibaca publik.

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

### Konfigurasi frontend dan token

Biarkan konfigurasi frontend kosong agar browser memanggil proxy Vercel:

```js
window.JADICEK_API_URL = "";
```

Tambahkan hanya `HF_TOKEN` sebagai secret di Vercel. `HF_SPACE_URL` bersifat opsional;
nilai defaultnya sudah mengarah ke `https://kevin-surya04-jadicek-api.hf.space`.

Pipeline LightGBM tetap melakukan inferensi di CPU. Namun, akun gratis yang hanya
dapat memakai hardware ZeroGPU mengharuskan fungsi Gradio terdaftar memakai dekorator
`@spaces.GPU`. Karena prediksi setelah model dimuat berlangsung sangat singkat,
`predict` memakai `@spaces.GPU(duration=1)` agar reservasi kuota per request minimal.
Jika kuota ZeroGPU pengguna sudah habis, request tetap ditolak sampai kuota direset.

Frontend tidak memanggil Space secara langsung. Proxy Vercel memakai endpoint Gradio
`/gradio_api/call/v2/predict` dengan token agar request ZeroGPU dihitung sebagai
pengguna Hugging Face terautentikasi.
