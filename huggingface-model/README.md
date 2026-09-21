---
library_name: lightgbm
tags:
- tabular-classification
- scikit-learn
- health
license: mit
---

# Jadicek BRFSS 2023

Dua pipeline LightGBM untuk klasifikasi diabetes dan riwayat penyakit jantung, direproduksi dari `satria_data - Copy.ipynb`.

## Files

- `diabetes_pipeline.joblib`
- `heart_pipeline.joblib`
- `notebook_pipeline.py` — transformer yang dibutuhkan ketika membuka joblib
- `metrics.json` — evaluasi lengkap dan semantik label
- `requirements.txt` — versi runtime yang digunakan

## Evaluation

| Task | Accuracy | Weighted precision | Weighted F1 |
|---|---:|---:|---:|
| Diabetes | 0.8412 | 0.8071 | 0.7986 |
| Heart disease | 0.9356 | 0.9046 | 0.9049 |

Label notebook: `0 = kondisi ada/riwayat`, `1 = kondisi tidak ada/borderline`. Target tidak seimbang. Accuracy dan weighted metrics yang tinggi tidak mewakili sensitivitas kelas penyakit; lihat `metrics.json` untuk disease-class recall dan confusion matrix.

Model ini merupakan hasil penelitian dan bukan alat diagnosis medis.
