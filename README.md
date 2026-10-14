# Eksplorasi Mahadata: prediksi beban listrik dengan Apache Spark

**Ray Regan Sitepu - 123140047 - kelas R**  
Institut Teknologi Sumatera, Teknik Informatika, IF25-40402.

Replikasi parsial alur Spark SQL dan Spark MLlib dalam:

Ali El-Sayed Ali, H., Alham, M. H., & Ibrahim, D. K. (2024). Big data resolving using Apache Spark for load forecasting and demand response in smart grid: A case study of Low Carbon London Project. *Journal of Big Data, 11*, Article 59. https://doi.org/10.1186/s40537-024-00909-6

## Status dan integritas

Eksperimen lokal benar-benar dijalankan; angka berasal dari keluaran program di `results/`.
Replikasi ini menggunakan subset CSV meter, bukan data lengkap/cuaca/ACORN/klaster artikel.
Kode, rancangan, pengujian, dan penulisan dibantu OpenAI Codex. Penggunaan bantuan AI
harus mengikuti izin dosen; mahasiswa perlu memahami dan memeriksa hasil sebelum mengumpulkan.
Tidak ada klaim hasil ini dikerjakan tanpa bantuan. Riwayat commit lokal, jika tersedia,
mencatat pembuatan paket ini dan bukan bukti pengerjaan historis sebelum percakapan.

## Isi folder

```text
src/experiment.py          Spark: pembersihan, agregasi, fitur, validasi, pengujian
src/make_report.py         Grafik dan laporan PDF/Markdown berdasarkan hasil nyata
Eksplorasi_Mahadata.ipynb  Notebook mandiri; agregat data disertakan di dalamnya
requirements.txt          Versi Python libraries yang digunakan
requirements-lock.txt     Versi lengkap dependensi pada eksekusi acuan
run.ps1                   Menjalankan eksperimen dan laporan di Windows
results/                  Agregat CSV, metrik, parameter, grafik, manifest, lingkungan
logs/                     Log eksperimen dan kendala teknis
docs/                     Laporan PDF dan sumber Markdown
```

## Lingkungan

Python 3.13, Spark/PySpark 4.0.1, **JDK 17 atau 21**, mode `local[2]`.
JDK 25 tidak termasuk versi Java yang didukung Spark 4.0.1.
Tidak membutuhkan Hadoop/HDFS, akun cloud, atau NoSQL: panduan membolehkan Spark dan/atau NoSQL.
Sediakan sekurangnya 4 GB heap JVM dan ruang untuk dependensi PySpark.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip --isolated install --no-cache-dir -r requirements.txt
$env:JAVA_HOME = 'C:\path\ke\jdk-21'
$env:SPARK_LOCAL_IP = '127.0.0.1'
```

## Menjalankan ulang dari CSV mentah

Dataset resmi: UK Power Networks, *SmartMeter Energy Consumption Data in London Households*,
London Datastore. https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d
Unduh ZIP versi **168 files**, ekstrak, dan arahkan `--data-dir` ke folder berisi
`LCL-June2015v2_0.csv` sampai `LCL-June2015v2_167.csv`.
Data terbuka berlisensi Creative Commons Attribution menurut portal; cantumkan atribusi sumber.
ZIP mentah 8,54 GB setelah ekstraksi tidak diduplikasi dalam paket tugas.

```powershell
.\.venv\Scripts\python.exe src\experiment.py --data-dir 'D:\tugas mahadata\Partitioned LCL Data\Small LCL Data' --output . --files 3 --households 50
.\.venv\Scripts\python.exe src\make_report.py
```

Di workspace asal, cukup jalankan dari folder paket:

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

## Menjalankan ulang model tanpa mengunduh CSV besar

Agregat hasil pembersihan sudah disertakan, dengan atribusi dataset di atas.
Ini mengulangi pemodelan, tetapi tidak mengulangi praproses mentah.

```powershell
.\.venv\Scripts\python.exe src\experiment.py --aggregate results\aggregate_2013.csv --output .
.\.venv\Scripts\python.exe src\make_report.py
```

Linux/macOS: gunakan `python3 -m venv .venv`, `.venv/bin/python -m pip install -r requirements.txt`,
lalu ganti executable dalam perintah di atas dengan `.venv/bin/python`. Tetapkan JAVA_HOME ke JDK yang sesuai.

## Protokol eksperimen

- Input: tiga CSV pertama berdasarkan nomor file, 3.000.000 baris. Partisi file bukan blok geografis artikel.
- Kohort: 50 ID Std pertama menurut urutan leksikografis yang memiliki cakupan >=98% pada 2013.
- Pemilihan kelengkapan tahunan merupakan keputusan kohort retrospektif; bukan simulasi perekrutan rumah di awal tahun.
- `Null`, nilai negatif, waktu invalid, dan ID kosong dibuang; nol dipertahankan karena tidak selalu berarti kesalahan meter.
- Duplikat ID/tarif/waktu, bila ada, dirata-ratakan. Interval agregat hanya dipakai jika 50 rumah lengkap.
- Target: jumlah energi 50 rumah dalam kWh per 30 menit, bukan kW. Untuk rata-rata daya kW, kalikan energi interval dengan 2.
- Fitur: kalender siklis, akhir pekan, dan energi yang teramati pada t-30 menit, t-1 hari, t-1 minggu.
- Lag memakai join waktu persis agar interval hilang tidak menggeser waktu.
- Latih: sebelum 1 September 2013; validasi: September-Oktober; uji: November-Desember.
- Pemilihan parameter memakai RMSE validasi; setelah itu model di-fit ulang pada latih+validasi.
- Evaluasi uji rolling satu langkah: energi masa lalu yang sudah teramati tersedia pada tiap waktu prediksi.
  Ini tidak sama dengan ramalan multi-langkah untuk dua bulan sekaligus.
- StandardScaler dan PolynomialExpansion berada dalam pipeline; scaler hanya di-fit pada data pelatihan.
- Metrik: MSE, RMSE, MAE, R2, WAPE; baseline persistence, musiman harian, musiman mingguan.
- Waktu satu eksekusi mencakup transformasi dan pengambilan keluaran; bukan benchmark klaster.

## Sumber kode dan pustaka

Implementasi dibuat untuk tugas ini berdasarkan deskripsi artikel dan dokumentasi resmi Apache Spark.
Tidak disalin dari repositori penulis (kode penulis tidak disertakan pada halaman artikel yang diperiksa).

- Spark 4.0.1: https://spark.apache.org/docs/4.0.1/
- LinearRegression: https://spark.apache.org/docs/4.0.1/api/python/reference/api/pyspark.ml.regression.LinearRegression.html
- DecisionTreeRegressor: https://spark.apache.org/docs/4.0.1/api/python/reference/api/pyspark.ml.regression.DecisionTreeRegressor.html
- Dataset dan atribusi: URL London Datastore di atas.
- Temurin JDK: https://adoptium.net/ (jika memakai JDK portabel pada workspace asal).

## Repositori dan laporan

Repositori tujuan: https://github.com/Raysitepu/Tugas-Mahadata

Laporan PDF tersedia di `docs/123140047_Ray-Regan-Sitepu_Eksplorasi-Mahadata.pdf`.
URL ini menjadi default pembuat laporan. Jika fork ke tujuan lain, ubah dengan:

```powershell
.\.venv\Scripts\python.exe src\make_report.py --repo-url https://github.com/USERNAME/NAMA-REPO
```

Pembuat laporan akan memperbarui bagian E dan sampul. Pastikan dosen dapat membuka repositori/notebook.
Jangan mengunggah `.venv`, `runtime`, atau seluruh data mentah. Tidak perlu memasukkan kredensial.

## Pemeriksaan hasil acuan

`src/verify_results.py` memeriksa timestamp unik, kohort tetap, lag waktu persis,
dan menghitung ulang semua metrik secara independen. Model telah diulang dari agregat di
folder kerja terpisah; nilai MSE/RMSE/MAE/R2/WAPE sama dalam toleransi 1e-12.
Waktu eksekusi bukan benchmark: 72,87 detik untuk alur mentah awal dan 41,72 detik untuk pengulangan model.
Timestamp sumber tidak menandai zona; UTC hanya aturan parsing Spark. Rekaman waktu berulang
diringkas dan daylight saving belum direkonstruksi. Grafik membiarkan gap uji terlihat.
