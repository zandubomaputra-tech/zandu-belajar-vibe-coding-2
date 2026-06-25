import base64
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")


def img_b64(filename, style="max-height:520px;width:auto;"):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f'<img src="data:image/png;base64,{data}" alt="{filename}" style="{style}">'


FLOWCHART_HTML = """
<div style="display:flex;align-items:center;gap:0;font-size:0.62em;">
  <div style="display:flex;flex-direction:column;align-items:center;gap:6px;flex:1;">
    <div class="flow-box">Data Loading &amp; QC</div>
    <div class="flow-arrow">↓</div>
    <div class="flow-box">Persiapan DEM (BATNAS)</div>
    <div class="flow-arrow">↓</div>
    <div class="flow-box">Koreksi Bouguer Sederhana<br><span style="font-size:0.85em;color:#666;">harmonica.bouguer_correction()</span></div>
    <div class="flow-arrow">↓</div>
    <div class="flow-box">Koreksi Terrain<br><span style="font-size:0.85em;color:#666;">Prism Forward Modeling</span></div>
    <div class="flow-arrow">↓</div>
    <div class="flow-box">Gridding<br><span style="font-size:0.85em;color:#666;">Equivalent Sources</span></div>
    <div class="flow-arrow">↓</div>
    <div class="flow-box flow-box--output">Peta Anomali Gravitasi</div>
  </div>
  <div style="flex:1;padding-left:32px;border-left:2px solid #e0e0e0;margin-left:16px;text-align:left;font-size:0.95em;line-height:1.8;">
    <p style="margin:0 0 8px 0;font-weight:600;color:#1a1a2e;">Software Stack</p>
    <p style="margin:0 0 4px 0;">Python 3.12 + Fatiando a Terra</p>
    <ul style="margin:0;padding-left:18px;color:#444;">
      <li>harmonica 0.7.0</li>
      <li>verde 1.9.0</li>
      <li>boule (normal gravity)</li>
      <li>matplotlib, cartopy</li>
    </ul>
    <p style="margin:12px 0 0 0;color:#888;font-size:0.9em;">Referensi:<br>Geosoft Oasis Montaj workflow</p>
  </div>
</div>
"""

SLIDES = [
    # Slide 1 — Title
    """<section data-background="linear-gradient(135deg,#0d1b2a 0%,#1a1a2e 50%,#16213e 100%)">
  <h1 style="color:#ffffff;font-size:2.2em;margin-bottom:0.3em;line-height:1.2;">
    Pengolahan Data Gravitasi Airborne
  </h1>
  <h3 style="color:#a0b4cc;font-size:1.1em;font-weight:400;margin-bottom:1.6em;">
    Wilayah Sulawesi Tengah, Indonesia
  </h3>
  <hr style="border:none;border-top:1px solid #2e4a6a;margin:0 auto 1.4em;width:60%;">
  <p style="color:#7a94ad;font-size:0.75em;">[Student Name] — Progress Report</p>
</section>""",

    # Slide 2 — Outline
    """<section>
  <h2>Outline</h2>
  <ol style="font-size:0.72em;line-height:2;columns:2;column-gap:3em;">
    <li>Pendahuluan &amp; Data Survey</li>
    <li>Metodologi Pengolahan</li>
    <li>Quality Control Data</li>
    <li>Persiapan DEM (Digital Elevation Model)</li>
    <li>Anomali Bouguer</li>
    <li>Koreksi Terrain</li>
    <li>Gridding (Equivalent Sources)</li>
    <li>Peta Anomali Gravitasi</li>
    <li>Hasil &amp; Interpretasi</li>
    <li>Kesimpulan &amp; Rencana Selanjutnya</li>
  </ol>
</section>""",

    # Slide 3 — Pendahuluan
    """<section>
  <h2>Pendahuluan</h2>
  <ul style="font-size:0.72em;line-height:1.9;">
    <li><strong>Tujuan:</strong> Mengolah data gravitasi airborne untuk menghasilkan peta anomali gravitasi</li>
    <li><strong>Wilayah:</strong> Sulawesi Tengah, Indonesia
      <ul style="margin-top:4px;">
        <li>Longitude: 120.80° – 124.10° BT</li>
        <li>Latitude: 2.10° LS – 0.003° LU</li>
      </ul>
    </li>
    <li><strong>Data:</strong> 48.806 titik pengamatan gravitasi airborne</li>
    <li>Mencakup wilayah darat dan laut (<em>mixed marine/land survey</em>)</li>
  </ul>
  <div style="margin-top:1.2em;display:inline-block;background:#f0f4f8;border:1px solid #c8d8e8;border-radius:8px;padding:10px 24px;font-size:0.62em;color:#555;">
    📍 Sulawesi Tengah &nbsp;|&nbsp; 120.8°–124.1° BT &nbsp;|&nbsp; 2.1° LS – 0° LU
  </div>
</section>""",

    # Slide 4 — Data Survey
    """<section>
  <h2>Data Survei Gravitasi Airborne</h2>
  <div style="display:flex;gap:2em;font-size:0.68em;align-items:flex-start;margin-top:0.5em;">
    <div style="flex:1;">
      <table style="width:100%;border-collapse:collapse;">
        <thead>
          <tr style="background:#1a1a2e;color:#fff;">
            <th style="padding:7px 10px;text-align:left;border-radius:4px 0 0 0;">Parameter</th>
            <th style="padding:7px 10px;text-align:left;border-radius:0 4px 0 0;">Nilai</th>
          </tr>
        </thead>
        <tbody>
          <tr style="background:#f5f7fa;"><td style="padding:6px 10px;">Jumlah titik</td><td style="padding:6px 10px;">48.806</td></tr>
          <tr><td style="padding:6px 10px;">Titik darat</td><td style="padding:6px 10px;">16.167 (33%)</td></tr>
          <tr style="background:#f5f7fa;"><td style="padding:6px 10px;">Titik laut</td><td style="padding:6px 10px;">32.639 (67%)</td></tr>
          <tr><td style="padding:6px 10px;">FAA range</td><td style="padding:6px 10px;">-149.12 s/d +240.63 mGal</td></tr>
          <tr style="background:#f5f7fa;"><td style="padding:6px 10px;">Elevasi</td><td style="padding:6px 10px;">-3.952 s/d +2.568 m</td></tr>
        </tbody>
      </table>
    </div>
    <div style="flex:1;background:#f0f4f8;border-left:4px solid #1a1a2e;border-radius:4px;padding:14px 16px;">
      <p style="margin:0 0 8px 0;font-weight:600;color:#1a1a2e;">Kolom Data</p>
      <p style="margin:0;line-height:1.9;color:#444;">
        Bujur (Longitude)<br>
        Lintang (Latitude)<br>
        FAA (Free Air Anomaly)<br>
        Elevation_m<br>
        UTM_X &nbsp;/&nbsp; UTM_Y
      </p>
      <p style="margin:14px 0 0 0;color:#888;font-size:0.9em;">Source: <code>gravity_filled.csv</code></p>
    </div>
  </div>
</section>""",

    # Slide 5 — Metodologi (HTML flowchart)
    f"""<section>
  <h2>Metodologi Pengolahan</h2>
  {FLOWCHART_HTML}
</section>""",

    # Slide 6 — QC
    f"""<section>
  <h2>Step 1 — Quality Control Data</h2>
  {img_b64("01_qc_report.png")}
  <p style="font-size:0.55em;color:#666;margin-top:0.5em;">
    QC Report: Distribusi FAA dan Elevasi. Tidak ditemukan outlier di luar 3×IQR.
  </p>
</section>""",

    # Slide 7 — DEM
    f"""<section>
  <h2>Step 2 — Persiapan DEM (BATNAS)</h2>
  {img_b64("02_dem_preview.png")}
  <ul style="font-size:0.58em;line-height:1.8;margin-top:0.5em;">
    <li>Sumber: BATNAS v1.5 (BIG Indonesia), resolusi ~6 arc-second (~185 m)</li>
    <li>2 tile digabungkan dan dipotong sesuai area survei</li>
    <li>Diproyeksikan ke UTM Zone 51S (EPSG:32751) untuk pemodelan prism</li>
    <li>Titik pengamatan gravitasi ditampilkan sebagai titik merah</li>
  </ul>
</section>""",

    # Slide 8 — Bouguer
    f"""<section>
  <h2>Step 3 — Koreksi Bouguer Sederhana</h2>
  {img_b64("03_bouguer_anomaly.png")}
  <ul style="font-size:0.58em;line-height:1.8;margin-top:0.5em;">
    <li>Koreksi Bouguer menghilangkan efek massa topografi</li>
    <li>Densitas kerak: 2.670 kg/m³ &nbsp;|&nbsp; Densitas air: 1.040 kg/m³</li>
    <li>Rumus: <code>SBA = FAA − Bouguer Correction</code></li>
    <li><code>harmonica.bouguer_correction()</code> menangani titik darat &amp; laut secara otomatis</li>
    <li>Hasil: SBA range -79.8 s/d +185.5 mGal</li>
  </ul>
</section>""",

    # Slide 9 — Terrain
    f"""<section>
  <h2>Step 4 — Koreksi Terrain (Prism Forward Modeling)</h2>
  {img_b64("04_terrain_correction.png")}
  <ul style="font-size:0.58em;line-height:1.8;margin-top:0.5em;">
    <li>DEM dimodelkan sebagai layer prisma (<code>harmonica.prism_layer</code>)</li>
    <li>Efek gravitasi topografi dihitung di setiap titik pengamatan</li>
    <li>Densitas kontras: 2.670 kg/m³ (darat), 1.630 kg/m³ (laut)</li>
    <li>Complete Bouguer Anomaly (CBA) = FAA − efek terrain</li>
    <li>CBA lebih halus dari SBA (std: 37.0 vs 38.8 mGal) ✓</li>
  </ul>
</section>""",

    # Slide 10 — Gridding
    f"""<section>
  <h2>Step 5 — Gridding (Equivalent Sources)</h2>
  {img_b64("05_gridded_maps.png")}
  <ul style="font-size:0.58em;line-height:1.8;margin-top:0.5em;">
    <li>Metode: Equivalent Sources (harmonica + verde)</li>
    <li>Data titik tersebar → grid reguler 2 km × 2 km</li>
    <li>Ketinggian prediksi: 2.600 m (<em>upward continuation</em>)</li>
    <li>Damping: 10 &nbsp;|&nbsp; Depth: 10.000 m</li>
    <li>Keunggulan: Interpolasi yang menghormati fisika medan potensial</li>
  </ul>
</section>""",

    # Slide 11 — FAA map
    f"""<section>
  <h2>Peta Anomali Free Air (FAA)</h2>
  {img_b64("06_faa_anomaly_map.png", style="max-height:480px;width:auto;")}
  <p style="font-size:0.55em;color:#555;margin-top:0.4em;font-style:italic;">
    Free Air Anomaly — Survei Gravitasi Airborne Sulawesi Tengah
  </p>
  <ul style="font-size:0.58em;line-height:1.7;text-align:left;margin-top:0.3em;">
    <li>Anomali positif tinggi (merah): area daratan dengan topografi tinggi</li>
    <li>Anomali negatif (biru): cekungan laut dalam</li>
    <li>Korelasi kuat dengan topografi — sesuai harapan untuk FAA</li>
  </ul>
</section>""",

    # Slide 12 — CBA map
    f"""<section>
  <h2>Peta Complete Bouguer Anomaly (CBA)</h2>
  {img_b64("06_cba_anomaly_map.png", style="max-height:480px;width:auto;")}
  <p style="font-size:0.55em;color:#555;margin-top:0.4em;font-style:italic;">
    Complete Bouguer Anomaly — menunjukkan variasi densitas bawah permukaan
  </p>
  <ul style="font-size:0.58em;line-height:1.7;text-align:left;margin-top:0.3em;">
    <li>Efek topografi telah dihilangkan</li>
    <li>Anomali yang tersisa mencerminkan variasi densitas di bawah permukaan</li>
    <li>Berguna untuk identifikasi struktur geologi: sesar, intrusi, cekungan</li>
  </ul>
</section>""",

    # Slide 13 — Combined
    f"""<section>
  <h2>Hasil Keseluruhan</h2>
  {img_b64("06_combined_report.png", style="max-height:500px;width:auto;")}
  <p style="font-size:0.55em;color:#555;margin-top:0.4em;">
    (a) Topografi/Batimetri &nbsp;|&nbsp; (b) FAA &nbsp;|&nbsp; (c) CBA &nbsp;|&nbsp; (d) Anomali Residual
  </p>
  <p style="font-size:0.55em;color:#888;">
    Panel (d) menunjukkan anomali residual setelah menghilangkan tren regional — mengungkap fitur geologis lokal
  </p>
</section>""",

    # Slide 14 — Conclusions
    """<section data-background="linear-gradient(135deg,#0d1b2a 0%,#1a1a2e 50%,#16213e 100%)">
  <h2 style="color:#ffffff;">Kesimpulan &amp; Rencana Selanjutnya</h2>
  <div style="display:flex;gap:2.5em;font-size:0.68em;margin-top:0.8em;text-align:left;">
    <div style="flex:1;">
      <p style="color:#a0b4cc;font-weight:600;margin-bottom:0.5em;">Kesimpulan</p>
      <p style="color:#e0e8f0;line-height:2;">
        ✅ Data gravitasi airborne berhasil diolah (48.806 titik)<br>
        ✅ Peta FAA dan CBA berhasil dihasilkan<br>
        ✅ Koreksi terrain menggunakan prism forward modeling<br>
        ✅ Gridding menggunakan Equivalent Sources (2 km)
      </p>
    </div>
    <div style="flex:1;border-left:1px solid #2e4a6a;padding-left:2em;">
      <p style="color:#a0b4cc;font-weight:600;margin-bottom:0.5em;">Rencana Selanjutnya</p>
      <p style="color:#c8d8e8;line-height:2;">
        → Pemisahan Regional–Residual (filtering frekuensi)<br>
        → Analisis derivatif (gradient horizontal, vertikal, tilt angle)<br>
        → Euler Deconvolution (estimasi kedalaman sumber)<br>
        → Analisis spektrum daya (estimasi kedalaman)<br>
        → Profil penampang 2D<br>
        → Interpretasi geologi
      </p>
    </div>
  </div>
</section>""",
]

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Pengolahan Data Gravitasi Airborne — Sulawesi Tengah</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/theme/white.css">
  <style>
    :root {
      --navy: #1a1a2e;
      --accent: #2e6da4;
    }
    .reveal { font-family: 'Inter', sans-serif; }
    .reveal h1, .reveal h2, .reveal h3 {
      font-family: 'Inter', sans-serif;
      color: var(--navy);
      text-transform: none;
      letter-spacing: -0.02em;
    }
    .reveal h2 { font-size: 1.5em; margin-bottom: 0.5em; }
    .reveal code { font-family: 'Fira Code', monospace; font-size: 0.88em;
                   background: #f0f4f8; padding: 1px 5px; border-radius: 3px; }
    .reveal ul { font-size: 0.7em; }
    .reveal li { margin-bottom: 0.2em; }
    .flow-box {
      background: #fff;
      border: 1px solid #c8d8e8;
      border-left: 4px solid var(--accent);
      border-radius: 5px;
      padding: 8px 18px;
      text-align: center;
      min-width: 240px;
      color: #1a1a2e;
      font-weight: 500;
      box-shadow: 0 1px 4px rgba(0,0,0,0.07);
    }
    .flow-box--output {
      border-left-color: #2a9d5c;
      background: #f0faf5;
      color: #1a4a30;
    }
    .flow-arrow { color: var(--accent); font-size: 1.3em; line-height: 1; }
    table { font-family: 'Inter', sans-serif; }
  </style>
</head>
<body>
<div class="reveal">
  <div class="slides">
SLIDES_PLACEHOLDER
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js"></script>
<script>
  Reveal.initialize({
    hash: true,
    slideNumber: 'c/t',
    width: 1280,
    height: 720,
    margin: 0.04,
    transition: 'slide',
    center: true,
  });
</script>
</body>
</html>
"""


def build():
    slides_html = "\n".join(f"    {s}" for s in SLIDES)
    html = HTML_TEMPLATE.replace("SLIDES_PLACEHOLDER", slides_html)
    out_path = os.path.join(OUTPUT_DIR, "presentation.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"Done: presentation.html written ({size_mb:.1f} MB, {len(SLIDES)} slides)")
    print(f"   Path: {os.path.abspath(out_path)}")


if __name__ == "__main__":
    build()
