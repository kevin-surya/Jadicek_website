from __future__ import annotations

import gradio as gr
import spaces

from model_service import ModelService


model = ModelService()


@spaces.GPU(duration=1)
def predict(payload: dict) -> dict:
    """Run both notebook-trained pipelines through one public Gradio endpoint."""
    if not isinstance(payload, dict):
        raise gr.Error("Input harus berupa objek JSON.")

    try:
        return model.predict(payload)
    except ValueError as exc:
        raise gr.Error(str(exc)) from exc
    except Exception as exc:
        raise gr.Error("Prediksi model gagal diproses.") from exc


example_payload = {
    "merokok": "tidak",
    "alkohol": "tidak",
    "bmi": 23.5,
    "olahraga": "ya",
    "tekanan_darah_tinggi": "tidak",
    "kolesterol_tinggi": "tidak",
    "jenis_klmn": "perempuan",
    "umur": "6.0",
    "susah_jalan": "tidak",
    "kesehatan_umum": "baik",
    "domisili": "1",
    "aktivitas_fisik": "aktif",
}


with gr.Blocks(title="JadiCek Prediction API") as demo:
    gr.Markdown(
        "# JadiCek Prediction API\n"
        "Prediksi diabetes dan penyakit jantung menggunakan pipeline LightGBM "
        "hasil notebook. Hasil model bukan diagnosis medis."
    )
    payload = gr.JSON(value=example_payload, label="Data pemeriksaan")
    submit = gr.Button("Jalankan prediksi", variant="primary")
    output = gr.JSON(label="Hasil prediksi")

    submit.click(
        fn=predict,
        inputs=payload,
        outputs=output,
        api_name="predict",
    )


if __name__ == "__main__":
    demo.launch()
