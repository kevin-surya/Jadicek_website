"use strict";

async function predictFromSpace(payload) {
  const spaceUrl = String(window.JADICEK_GRADIO_URL || '').replace(/\/$/, '');
  if (!spaceUrl) return null;

  const start = await fetch(`${spaceUrl}/gradio_api/call/predict`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({data: [payload]}),
    signal: AbortSignal.timeout(30000)
  });
  if (!start.ok) throw new Error(`space-start-${start.status}`);

  const {event_id: eventId} = await start.json();
  if (!eventId) throw new Error('space-event-id');

  const result = await fetch(`${spaceUrl}/gradio_api/call/predict/${encodeURIComponent(eventId)}`, {
    signal: AbortSignal.timeout(60000)
  });
  if (!result.ok) throw new Error(`space-result-${result.status}`);

  const stream = await result.text();
  const complete = stream.match(/event: complete\r?\ndata: (.+)(?:\r?\n|$)/);
  if (!complete) {
    const failure = stream.match(/event: error\r?\ndata: (.+)(?:\r?\n|$)/);
    if (failure) throw new Error('space-prediction-error');
    throw new Error('space-response-format');
  }

  const data = JSON.parse(complete[1]);
  return Array.isArray(data) ? data[0] : data;
}

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
  let message = 'Kami belum dapat menghitung hasil kesehatan Anda saat ini. Jawaban Anda tetap tersimpan di halaman ini dan Anda dapat mencobanya lagi nanti.';
  try {
    let data = await predictFromSpace(input.payload);
    if (!data) {
      const apiBase = String(window.JADICEK_API_URL || '').replace(/\/$/, '');
      const response = await fetch(`${apiBase}/api/predict`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify(input.payload), signal:AbortSignal.timeout(30000)
      });
      if (response.ok) data = await response.json();
      else throw new Error(`api-${response.status}`);
    }
    if (data) {
      if (typeof data.diabetes_result !== 'string' || typeof data.heart_result !== 'string') throw new Error('format');
      prediction = {diabetes_result:data.diabetes_result, heart_result:data.heart_result,
        diabetes_score:data.diabetes_score, heart_score:data.heart_score};
      message = 'Hasil ini membantu Anda mengenali hal yang mungkin perlu diperhatikan. Ini bukan diagnosis medis.';
    }
  } catch (error) {
    message = 'Kami belum dapat menampilkan hasil kesehatan Anda saat ini. Periksa koneksi internet, lalu coba kembali beberapa saat lagi.';
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
  const diabetesResult = getFriendlyResult(p && p.diabetes_score);
  const heartResult = getFriendlyResult(p && p.heart_score);
  const resultCard = (condition, healthResult) => `<div class="result-box"><span>${condition}</span><strong>${p ? healthResult.title : 'Belum dapat dihitung'}</strong><p>${p ? healthResult.description : 'Silakan coba kembali beberapa saat lagi.'}</p></div>`;
  result.innerHTML = `<span class="result-badge">RINGKASAN ANDA</span><h3>Yuk, kenali kondisi kesehatan Anda.</h3><p>Kami merangkum jawaban Anda agar hasilnya lebih mudah dipahami.</p><div class="result-grid"><div class="result-box"><span>Indeks massa tubuh (BMI)</span><strong>${latest.payload.bmi.toFixed(2)}</strong><p>Perbandingan berat dan tinggi badan Anda.</p></div><div class="result-box"><span>Status hasil</span><strong>${p ? 'Sudah selesai' : 'Belum dapat dihitung'}</strong><p>${p ? 'Berikut hal yang dapat Anda perhatikan.' : 'Jawaban Anda tetap tersedia di halaman ini.'}</p></div></div><div class="result-grid">${resultCard('Diabetes', diabetesResult)}${resultCard('Penyakit jantung', heartResult)}</div><div class="result-message">${escapeText(message)}</div><dl class="result-summary">${summary}</dl><p class="result-disclaimer">Angka di atas menunjukkan tingkat kemiripan jawaban Anda dengan pola yang dipelajari sistem, bukan persentase risiko Anda terkena penyakit. Untuk mengetahui kondisi kesehatan secara pasti, konsultasikan dengan tenaga kesehatan.</p><div class="result-actions"><button class="button" id="download">Unduh ringkasan <span>↓</span></button><button class="button result-secondary" id="edit">Ubah jawaban</button><button class="back-button" id="reset">Mulai ulang</button></div>`;
  document.querySelector('#download').addEventListener('click', () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(latest, null, 2)], {type:'application/json'}));
    const link = document.createElement('a'); link.href = url; link.download = 'ringkasan-jadicek.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  document.querySelector('#edit').addEventListener('click', () => restore(false));
  document.querySelector('#reset').addEventListener('click', () => restore(true));
  result.focus({preventScroll:true});
}
function getFriendlyResult(score) {
  if (!Number.isFinite(score)) return {title: 'Hasil tersedia', description: 'Lihat ringkasan hasil pemeriksaan Anda.'};
  const value = (score * 100).toFixed(1);
  if (score < 0.35) return {
    title: 'Cenderung rendah',
    description: `Hasil perhitungan ${value}%. Pola jawaban Anda tidak menunjukkan banyak tanda yang berkaitan dengan kondisi ini.`
  };
  if (score < 0.65) return {
    title: 'Perlu diperhatikan',
    description: `Hasil perhitungan ${value}%. Ada beberapa tanda yang sebaiknya Anda perhatikan dan pantau.`
  };
  return {
    title: 'Sebaiknya ditindaklanjuti',
    description: `Hasil perhitungan ${value}%. Pertimbangkan untuk berkonsultasi dengan tenaga kesehatan.`
  };
}
function restore(reset) {
  if (reset) {form.reset(); latest = null;}
  result.hidden = true; result.innerHTML = ''; form.hidden = false; step = 0; showStep();
}
