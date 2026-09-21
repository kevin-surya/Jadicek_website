"use strict";
const form = document.querySelector('#check-form');
const fieldsets = [...form.querySelectorAll('fieldset')];
const next = document.querySelector('#next');
const back = document.querySelector('#back');
const result = document.querySelector('#result');
let step = 0;
let latest = null;
const menu = document.querySelector('.menu');
menu.addEventListener('click', () => {
  const open = document.querySelector('nav').classList.toggle('open');
  menu.setAttribute('aria-expanded', String(open));
});
document.querySelectorAll('nav a').forEach(a => a.addEventListener('click', () => {
  document.querySelector('nav').classList.remove('open');
  menu.setAttribute('aria-expanded', 'false');
}));
function showStep(focus = true) {
  fieldsets.forEach((f, i) => {
    f.hidden = i !== step;
    f.disabled = i !== step;
  });
  document.querySelectorAll('#steps li').forEach((li, i) => {
    li.classList.toggle('active', i === step);
    li.classList.toggle('done', i < step);
    if (i === step) li.setAttribute('aria-current', 'step');
    else li.removeAttribute('aria-current');
  });
  back.hidden = step === 0;
  document.querySelector('#step-label').textContent = `${step + 1} dari 3 langkah`;
  next.innerHTML = step === 2 ? 'Lihat hasil <span>↗</span>' : 'Lanjutkan <span>→</span>';
  if (focus) fieldsets[step].querySelector('input, select').focus({preventScroll:true});
}
showStep(false);
back.addEventListener('click', () => { step--; showStep(); });
function getInput() {
  const values = {};
  form.querySelectorAll('[name]').forEach(el => { values[el.name] = el.value; });
  const age = Number(values.usia);
  const ageBucket = age <= 24 ? 1 : Math.min(14, Math.floor((age - 25) / 5) + 2);
  const bmi = Number((Number(values.berat) / (Number(values.tinggi) / 100) ** 2).toFixed(2));
  const {usia, tinggi, berat, ...rest} = values;
  return {profile: values, payload: {...rest, bmi, umur: `${ageBucket}.0`}};
}
function escapeText(value) {
  return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
form.addEventListener('submit', async e => {
  e.preventDefault();
  if (!form.reportValidity()) return;
  if (step < 2) { step++; showStep(); return; }
  next.disabled = true; back.disabled = true;
  next.textContent = 'Memproses…';
  const input = getInput();
  let prediction = null;
  let message = 'Layanan model belum terhubung. Ringkasan Anda tersedia; prediksi diabetes dan jantung belum dapat dihitung.';
  try {
    const response = await fetch('/api/predict', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify(input.payload), signal:AbortSignal.timeout(30000)
    });
    if (response.ok) {
      const data = await response.json();
      if (typeof data.diabetes_result !== 'string' || typeof data.heart_result !== 'string') throw new Error('format');
      prediction = {diabetes_result:data.diabetes_result, heart_result:data.heart_result,
        diabetes_score:data.diabetes_score, heart_score:data.heart_score};
      message = 'Prediksi diterima dari layanan model. Hasil ini bukan diagnosis medis.';
    } else if (response.status !== 503 && response.status !== 404 && response.status !== 405) {
      message = 'Layanan prediksi sedang mengalami kendala. Ringkasan Anda tetap tersedia. Silakan coba kembali.';
    }
  } catch (error) {
    message = 'Layanan prediksi tidak dapat dihubungi atau format hasilnya tidak sesuai. Ringkasan Anda tetap tersedia.';
  } finally {
    next.disabled = false; back.disabled = false; showStep(false);
  }
  latest = {...input, prediction, created_at: new Date().toISOString()};
  renderResult(message);
});
function renderResult(message) {
  form.hidden = true;
  result.hidden = false;
  const p = latest.prediction;
  const summary = [...form.querySelectorAll('[name]')].map(el => {
    const label = el.closest('label').childNodes[0].textContent.trim();
    const value = el.tagName === 'SELECT' ? el.selectedOptions[0].textContent : el.value;
    return `<div><dt>${escapeText(label)}</dt><dd>${escapeText(value)}</dd></div>`;
  }).join('');
  const diabetesScore = p && Number.isFinite(p.diabetes_score) ? ` · skor ${(p.diabetes_score * 100).toFixed(1)}%` : '';
  const heartScore = p && Number.isFinite(p.heart_score) ? ` · skor ${(p.heart_score * 100).toFixed(1)}%` : '';
  result.innerHTML = `<span class="result-badge">PEMERIKSAAN ANDA</span><h3>Satu langkah lebih mengenal diri.</h3><p>Berikut ringkasan berdasarkan informasi yang Anda berikan.</p><div class="result-grid"><div class="result-box"><span>Indeks massa tubuh</span><strong>${latest.payload.bmi.toFixed(2)}</strong><p>BMI = berat (kg) / tinggi (m)²</p></div><div class="result-box"><span>Status pemeriksaan</span><strong>${p ? 'Hasil tersedia' : 'Profil lengkap'}</strong><p>${p ? 'Terhubung ke model lokal' : 'Menunggu layanan model'}</p></div></div><div class="result-grid"><div class="result-box"><span>Diabetes${diabetesScore}</span><strong>${p ? escapeText(p.diabetes_result) : 'Belum tersedia'}</strong></div><div class="result-box"><span>Penyakit jantung${heartScore}</span><strong>${p ? escapeText(p.heart_result) : 'Belum tersedia'}</strong></div></div><div class="result-message">${escapeText(message)}</div><dl class="result-summary">${summary}</dl><p>Skor adalah probabilitas keluaran model untuk kelas penyakit, bukan persentase risiko klinis. Ringkasan ini tidak menggantikan pemeriksaan tenaga kesehatan.</p><div class="result-actions"><button class="button" id="download">Unduh ringkasan <span>↓</span></button><button class="button result-secondary" id="edit">Ubah jawaban</button><button class="back-button" id="reset">Mulai ulang</button></div>`;
  document.querySelector('#download').addEventListener('click', () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(latest, null, 2)], {type:'application/json'}));
    const link = document.createElement('a'); link.href = url; link.download = 'ringkasan-jadicek.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  document.querySelector('#edit').addEventListener('click', () => restore(false));
  document.querySelector('#reset').addEventListener('click', () => restore(true));
  result.focus({preventScroll:true});
}
function restore(reset) {
  if (reset) {form.reset(); latest = null;}
  result.hidden = true; result.innerHTML = ''; form.hidden = false; step = 0; showStep();
}
