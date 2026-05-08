# Implementation Plan: Academic Progress Presentation

> **For Claude Code**: Build a self-contained HTML slide presentation.
> The presentation will be shown to a university lecturer as a progress report
> on airborne gravity data processing work.

---

## What to Build

A **single-file HTML presentation** using [Reveal.js CDN](https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/) — no npm install needed.
All images are embedded as base64 data URIs so the HTML file is fully portable.

**Script**: `scripts/build_presentation.py`
**Output**: `output/presentation.html`

---

## Technical Approach

Use Python to:
1. Read each PNG figure from `output/` and encode to base64
2. Generate an HTML file with Reveal.js loaded from CDN
3. Embed all images inline as `<img src="data:image/png;base64,...">"`

```python
import base64
import os

def img_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def embed_img(path, alt="", style="max-height:520px;"):
    b64 = img_to_base64(path)
    return f'<img src="data:image/png;base64,{b64}" alt="{alt}" style="{style}">'
```

---

## Slide Structure (14 slides)

Below is the EXACT content for each slide. Follow this precisely.

### Slide 1 — Title Slide
```
Title: Pengolahan Data Gravitasi Airborne
Subtitle: Wilayah Sulawesi Tengah, Indonesia
Bottom line: [Student Name] — Progress Report
Style: Centered, large title, dark gradient background
```
- Use a dark navy/slate gradient background for the title slide
- Title in white, large font
- Subtitle smaller, light gray
- Leave "[Student Name]" as-is — the student will fill it in

### Slide 2 — Outline / Daftar Isi
```
Title: Outline
Bullet list:
1. Pendahuluan & Data Survey
2. Metodologi Pengolahan
3. Quality Control Data
4. Persiapan DEM (Digital Elevation Model)
5. Anomali Bouguer
6. Koreksi Terrain
7. Gridding (Equivalent Sources)
8. Peta Anomali Gravitasi
9. Hasil & Interpretasi
10. Kesimpulan & Rencana Selanjutnya
```

### Slide 3 — Pendahuluan
```
Title: Pendahuluan
Content:
- Tujuan: Mengolah data gravitasi airborne untuk menghasilkan peta anomali gravitasi
- Wilayah: Sulawesi Tengah, Indonesia
  - Longitude: 120.80° – 124.10° BT
  - Latitude: 2.10° LS – 0.003° LU
- Data: 48.806 titik pengamatan gravitasi airborne
- Mencakup wilayah darat dan laut (mixed marine/land survey)
```
- Add a simple location map or text indicator showing the region

### Slide 4 — Data Survey
```
Title: Data Survei Gravitasi Airborne
Two-column layout:
Left column — Data overview table:
  | Parameter | Nilai |
  |-----------|-------|
  | Jumlah titik | 48.806 |
  | Titik darat | 16.167 (33%) |
  | Titik laut | 32.639 (67%) |
  | FAA range | -149.12 s/d +240.63 mGal |
  | Elevasi | -3.952 s/d +2.568 m |

Right column — Data columns:
  Bujur (Longitude), Lintang (Latitude),
  FAA (Free Air Anomaly), Elevation_m,
  UTM_X, UTM_Y

Bottom: Source file: gravity_filled.csv
```

### Slide 5 — Metodologi
```
Title: Metodologi Pengolahan
Show a flowchart/pipeline diagram. Create this as an SVG or HTML diagram:

  Data Loading & QC
       ↓
  Persiapan DEM (BATNAS)
       ↓
  Koreksi Bouguer Sederhana
  (harmonica.bouguer_correction)
       ↓
  Koreksi Terrain
  (Prism Forward Modeling)
       ↓
  Gridding
  (Equivalent Sources)
       ↓
  Peta Anomali Gravitasi

Right side note:
  Software: Python 3.12 + Fatiando a Terra
  - harmonica 0.7.0
  - verde 1.9.0
  - boule (normal gravity)
  - matplotlib, cartopy (visualisasi)

  Referensi: Geosoft Oasis Montaj workflow
```
- Build the flowchart using HTML/CSS boxes with arrows, not an image
- Style with a clean, modern look — light boxes with colored left borders

### Slide 6 — Quality Control
```
Title: Step 1 — Quality Control Data
Embed image: output/01_qc_report.png
Caption below: "QC Report: Distribusi FAA dan Elevasi. Tidak ditemukan outlier di luar 3×IQR."
```

### Slide 7 — DEM Preparation
```
Title: Step 2 — Persiapan DEM (BATNAS)
Embed image: output/02_dem_preview.png
Bullet points below:
- Sumber: BATNAS v1.5 (BIG Indonesia), resolusi ~6 arc-second (~185 m)
- 2 tile digabungkan dan dipotong sesuai area survei
- Diproyeksikan ke UTM Zone 51S (EPSG:32751) untuk pemodelan prism
- Titik pengamatan gravitasi ditampilkan sebagai titik merah
```

### Slide 8 — Anomali Bouguer
```
Title: Step 3 — Koreksi Bouguer Sederhana
Embed image: output/03_bouguer_anomaly.png
Key points:
- Koreksi Bouguer menghilangkan efek massa topografi
- Densitas kerak: 2.670 kg/m³ | Densitas air: 1.040 kg/m³
- Rumus: SBA = FAA − Bouguer Correction
- harmonica.bouguer_correction() menangani titik darat & laut secara otomatis
- Hasil: SBA range -79.8 s/d +185.5 mGal
```

### Slide 9 — Koreksi Terrain
```
Title: Step 4 — Koreksi Terrain (Prism Forward Modeling)
Embed image: output/04_terrain_correction.png
Key points:
- DEM dimodelkan sebagai layer prisma (harmonica.prism_layer)
- Efek gravitasi topografi dihitung di setiap titik pengamatan
- Densitas kontras: 2.670 kg/m³ (darat), 1.630 kg/m³ (laut)
- Complete Bouguer Anomaly (CBA) = FAA − efek terrain
- CBA lebih halus dari SBA (std: 37.0 vs 38.8 mGal) ✓
```

### Slide 10 — Gridding
```
Title: Step 5 — Gridding (Equivalent Sources)
Embed image: output/05_gridded_maps.png
Key points:
- Metode: Equivalent Sources (harmonica + verde)
- Data titik tersebar → grid reguler 2 km × 2 km
- Ketinggian prediksi: 2.600 m (upward continuation)
- Damping: 10, Depth: 10.000 m
- Keunggulan: Interpolasi yang menghormati fisika medan potensial
```

### Slide 11 — Peta FAA
```
Title: Peta Anomali Free Air (FAA)
Embed image: output/06_faa_anomaly_map.png (full size, centered)
Caption: "Free Air Anomaly — Survei Gravitasi Airborne Sulawesi Tengah"
Brief interpretation:
- Anomali positif tinggi (merah): area daratan dengan topografi tinggi
- Anomali negatif (biru): cekungan laut dalam
- Korelasi kuat dengan topografi — sesuai harapan untuk FAA
```

### Slide 12 — Peta CBA
```
Title: Peta Complete Bouguer Anomaly (CBA)
Embed image: output/06_cba_anomaly_map.png (full size, centered)
Caption: "Complete Bouguer Anomaly — menunjukkan variasi densitas bawah permukaan"
Brief interpretation:
- Efek topografi telah dihilangkan
- Anomali yang tersisa mencerminkan variasi densitas di bawah permukaan
- Berguna untuk identifikasi struktur geologi: sesar, intrusi, cekungan
```

### Slide 13 — Hasil Gabungan
```
Title: Hasil Keseluruhan
Embed image: output/06_combined_report.png (full width)
Caption: "(a) Topografi/Batimetri, (b) FAA, (c) CBA, (d) Anomali Residual"
Note: Panel (d) menunjukkan anomali residual setelah menghilangkan tren regional
      — mengungkap fitur geologis lokal
```

### Slide 14 — Kesimpulan & Rencana
```
Title: Kesimpulan & Rencana Selanjutnya

Kesimpulan:
✅ Data gravitasi airborne berhasil diolah (48.806 titik)
✅ Peta FAA dan CBA berhasil dihasilkan
✅ Koreksi terrain menggunakan prism forward modeling
✅ Gridding menggunakan Equivalent Sources (2 km)

Rencana Selanjutnya:
→ Pemisahan Regional–Residual (filtering frekuensi)
→ Analisis derivatif (gradient horizontal, vertikal, tilt angle)
→ Euler Deconvolution (estimasi kedalaman sumber)
→ Analisis spektrum daya (estimasi kedalaman)
→ Profil penampang 2D
→ Interpretasi geologi
```

---

## HTML/CSS Requirements

### Reveal.js Setup
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/theme/white.css">
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js"></script>
```

### Styling Rules
1. **Font**: Use Google Fonts — `Inter` for body, `Fira Code` for code/data
2. **Color scheme**: Dark navy (#1a1a2e) for headers, white/light gray backgrounds
3. **Slide backgrounds**: White for content slides, dark gradient for title/conclusion
4. **Images**: Center horizontally, max-height 520px to leave room for captions
5. **Tables**: Clean borders, alternating row colors, compact
6. **Bullet points**: Use emoji checkmarks (✅) and arrows (→) for visual appeal
7. **Font sizes**: Title 2.2em, subtitle 1.2em, body text 0.7em, captions 0.55em
8. **Slide numbers**: Show at bottom-right
9. **Transitions**: Slide transition (default Reveal.js)
10. **Responsive**: Slides should look good at 1920×1080

### Reveal.js Config
```javascript
Reveal.initialize({
    hash: true,
    slideNumber: 'c/t',
    width: 1280,
    height: 720,
    margin: 0.04,
    transition: 'slide',
    center: true,
});
```

---

## Build Script Requirements

The script `scripts/build_presentation.py` must:
1. Read all PNG files from `output/` and convert to base64
2. Generate the complete HTML string with all slides
3. Write to `output/presentation.html`
4. Print the file size and slide count when done
5. Use `matplotlib.use("Agg")` is NOT needed — this script does not plot anything
6. The HTML must be fully self-contained (no local file references except CDN links for Reveal.js)

---

## Verification

After building, the student should be able to:
1. Double-click `output/presentation.html` in any browser
2. See all 14 slides with embedded images
3. Navigate with arrow keys or mouse clicks
4. Present in fullscreen (press F in Reveal.js)
