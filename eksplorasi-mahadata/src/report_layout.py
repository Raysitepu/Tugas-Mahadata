"""Susunan laporan mengikuti contoh pengguna; seluruh hasil tetap dari eksperimen LCL."""
import hashlib
import json
import os
from pathlib import Path
from xml.sax.saxutils import escape
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether


def build_report(root, repo_url, chart_builder, notebook_builder):
    r=root/'results';d=root/'docs';d.mkdir(exist_ok=True)
    chart_builder()
    profile=json.loads((r/'profile.json').read_text())
    env=json.loads((r/'environment.json').read_text())
    splits=json.loads((r/'split_counts.json').read_text())
    runtime=json.loads((r/'run_summary.json').read_text())
    configs=json.loads((r/'selected_configs.json').read_text())
    metrics=pd.read_csv(r/'test_metrics.csv')
    trials=pd.read_csv(r/'validation_trials.csv')
    hourly=pd.read_csv(r/'hourly_profile.csv');monthly=pd.read_csv(r/'monthly_profile.csv')
    weekend=pd.read_csv(r/'weekend_profile.csv')
    best=metrics.iloc[0];base=metrics[metrics.model=='Persistence-30min'].iloc[0]
    tree=metrics[metrics.model=='DTR'].iloc[0]
    improvement=100*(base.RMSE-best.RMSE)/base.RMSE
    peak=hourly.loc[hourly.mean_kwh.idxmax()];low=hourly.loc[hourly.mean_kwh.idxmin()]
    mh=monthly.loc[monthly.mean_kwh.idxmax()];ml=monthly.loc[monthly.mean_kwh.idxmin()]
    wd=100*(weekend.loc[weekend.day_type=='Weekend','mean_kwh'].iloc[0]/weekend.loc[weekend.day_type=='Hari kerja','mean_kwh'].iloc[0]-1)
    count=lambda x:f'{x:,.0f}'.replace(',','.')
    num=lambda x,n=3:f'{x:.{n}f}'.replace('.',',')
    paper='https://doi.org/10.1186/s40537-024-00909-6'
    data='https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d'
    output=d/'123140047_Ray-Regan-Sitepu_Eksplorasi-Mahadata.pdf'
    fonts=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'
    if (fonts/'times.ttf').exists():
        for name,file in [('Academic','times.ttf'),('AcademicBold','timesbd.ttf'),('AcademicItalic','timesi.ttf')]:
            pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
        pdfmetrics.registerFontFamily('Academic',normal='Academic',bold='AcademicBold',italic='AcademicItalic',boldItalic='AcademicBold')
        font,bold='Academic','AcademicBold'
    else:font,bold='Times-Roman','Times-Bold'
    styles={
        'body':ParagraphStyle('BodyAcademic',fontName=font,fontSize=11,leading=13.2,spaceAfter=8,alignment=TA_JUSTIFY),
        'h1':ParagraphStyle('MainHeading',fontName=bold,fontSize=13,leading=17,spaceAfter=11,keepWithNext=True),
        'h2':ParagraphStyle('Subheading',fontName=bold,fontSize=11.5,leading=15,spaceBefore=8,spaceAfter=7,keepWithNext=True),
        'caption':ParagraphStyle('CaptionAcademic',fontName=font,fontSize=9.5,leading=12,spaceBefore=5,spaceAfter=6),
        'cell':ParagraphStyle('CellAcademic',fontName=font,fontSize=9.5,leading=11.5),
        'small':ParagraphStyle('SmallAcademic',fontName=font,fontSize=9.5,leading=12,spaceAfter=6,alignment=TA_JUSTIFY),
        'ref':ParagraphStyle('ReferenceAcademic',fontName=font,fontSize=9.5,leading=12,spaceAfter=7,leftIndent=13,firstLineIndent=-13),
        'cover_top':ParagraphStyle('CoverTitle',fontName=bold,fontSize=17,leading=21,alignment=TA_CENTER,spaceAfter=18),
        'cover_topic':ParagraphStyle('CoverTopic',fontName=bold,fontSize=15,leading=19,alignment=TA_CENTER,spaceAfter=15),
        'cover':ParagraphStyle('CoverMetadata',fontName=font,fontSize=11,leading=15,alignment=TA_CENTER,spaceAfter=12),
        'cover_bold':ParagraphStyle('CoverIdentity',fontName=bold,fontSize=12,leading=16,alignment=TA_CENTER,spaceAfter=12),
        'code':ParagraphStyle('CodeAcademic',fontName='Courier',fontSize=8.5,leading=12,spaceAfter=8,backColor=colors.HexColor('#F3F3F3'),borderPadding=7),
    }
    left=30*mm;right=26.5*mm;w=A4[0]-left-right
    story=[];md=[]
    def normalize(text):
        return str(text).translate(str.maketrans({'\u2011':'-','\u2013':'-','\u2014':'-','\u2212':'-'}))
    def p(text,kind='body',markup=False):
        text=normalize(text)
        story.append(Paragraph((text if markup else escape(text)).replace('\n','<br/>'),styles[kind]))
        md.append(text+'\n')
    def h(text,level=1):p(text,'h1' if level==1 else 'h2');md[-1]='#'*level+' '+text+'\n'
    def page():story.append(PageBreak());md.append('\n---\n')
    def table(caption,headers,rows,ratios):
        # Caption, header and first data row stay on the same page.
        caption=normalize(caption)
        cap=Paragraph(escape(caption),styles['caption'])
        values=[[Paragraph(escape(normalize(x)),styles['cell']) for x in headers]]+[
            [Paragraph(escape(normalize(x)),styles['cell']) for x in row] for row in rows]
        t=Table(values,colWidths=[w*x for x in ratios],repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#ECECEC')),
            ('FONTNAME',(0,0),(-1,0),bold),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
            ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
            ('GRID',(0,0),(-1,-1),.4,colors.HexColor('#909090'))]))
        story.extend([KeepTogether([cap,t]),Spacer(1,8)])
        md.append(caption+'\n\n| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+
                  '\n'.join('| '+' | '.join(map(str,row))+' |' for row in rows)+'\n')
    def picture(file,height,caption):
        caption=normalize(caption)
        im=Image(str(r/file),width=w,height=height,kind='proportional')
        cap=Paragraph(escape(caption),styles['caption'])
        story.append(KeepTogether([im,cap,Spacer(1,5)]))
        md.append(f'![{caption}](../results/{file})\n')

    # Cover follows the supplied document's hierarchy and centered identity block.
    p('LAPORAN TUGAS\nEKSPLORASI MANDIRI MAHADATA','cover_top')
    p('REPLIKASI PARSIAL PREDIKSI BEBAN LISTRIK\nLOW CARBON LONDON MENGGUNAKAN\nAPACHE SPARK SQL DAN MLLIB','cover_topic')
    p('Mengacu pada Ali El-Sayed Ali et al. (2024)\nDOI: 10.1186/s40537-024-00909-6','cover')
    story.append(Spacer(1,8))
    logo=root/'assets/it-era-reference-logo.png'
    if logo.exists():
        im=Image(str(logo),width=39.5*mm,height=50*mm,kind='proportional');im.hAlign='CENTER';story.append(im)
    story.append(Spacer(1,21))
    p('Disusun oleh\n\nRAY REGAN SITEPU\nNIM 123140047\nKelas R','cover_bold')
    story.append(Spacer(1,22))
    p('PROGRAM STUDI TEKNIK INFORMATIKA\nFAKULTAS TEKNOLOGI INDUSTRI\nINSTITUT TEKNOLOGI SUMATERA\n2026','cover_bold')

    page();h('I. RINGKASAN JURNAL')
    h('1.1 Identitas dan Permasalahan Penelitian',2)
    p('Artikel utama ialah “Big data resolving using Apache Spark for load forecasting and demand response in smart grid: '
      'A case study of Low Carbon London Project” oleh Hussien Ali El-Sayed Ali, M. H. Alham, dan Doaa Khalil Ibrahim. '
      'Artikel diterbitkan pada Journal of Big Data, volume 11, artikel 59, tahun 2024, dengan DOI 10.1186/s40537-024-00909-6 '
      '(Ali El-Sayed Ali et al., 2024).')
    p('Permasalahan yang diangkat ialah pengolahan rekaman meter berskala besar untuk prediksi beban dan evaluasi respons permintaan. '
      'Jurnal diterbitkan Springer Nature dan terindeks Scopus serta SCIE menurut halaman penerbit. Daftar SCImago kategori '
      'Information Systems yang memuat data 2024 menampilkan Q1 dengan SJR 1,979. Received tercatat 26 Agustus 2023, '
      'accepted 7 April 2024, dan tanggal terbit 28 April 2024 (Springer Nature, n.d.; SCImago, n.d.).')
    h('1.2 Dataset, Lingkungan, dan Metode',2)
    p('Penelitian menggunakan rekaman LCL dari 5.567 rumah, dengan cuaca, ACORN, dan kalender. Spark SQL mendukung analisis '
      'deskriptif, sedangkan MLlib menjalankan regresi polinomial dan decision tree. Dataproc memakai satu master dan tiga worker; '
      'masing-masing memiliki 2 vCPU dan RAM 7,5 GB (Ali El-Sayed Ali et al., 2024).')
    p('Sebagai dasar replikasi, laporan ini memisahkan pengolahan rekaman meter, pembentukan target agregat, serta evaluasi model. '
      'Data mentah yang tersedia berisi ID rumah, kategori tarif, waktu, dan energi kWh per setengah jam. Cuaca serta pemetaan '
      'ACORN tidak tersedia pada folder kerja. Karena itu, fitur tambahan dirancang dari kalender dan energi masa lalu, '
      'dengan penjelasan eksplisit mengenai batas perbandingan.')
    h('1.3 Hasil Utama Artikel dan Alasan Pemilihan',2)
    p('Ridge pada Tabel 6 artikel mencapai R2 0,965 untuk seluruh rumah dan 0,943 untuk Block #0. Angka tersebut adalah '
      'hasil penelitian asli. Artikel menekankan manfaat agregasi serta keterbatasan untuk kelompok rumah kecil '
      '(Ali El-Sayed Ali et al., 2024).')
    p('Artikel dipilih karena datasetnya sudah tersedia dan bagian inti dapat dijalankan dengan Spark lokal. Sasaran eksperimen '
      'adalah memeriksa apakah prediksi 30 menit berikutnya pada 50 rumah lebih baik daripada baseline energi sebelumnya; '
      'membandingkan regularisasi dan kedalaman pohon; serta menjelaskan perbedaan hasil dengan artikel tanpa merekayasa angka.')

    page();h('II. TAHAPAN IMPLEMENTASI ATAU EKSPERIMEN')
    h('2.1 Bentuk Replikasi dan Sasaran',2)
    p('Pekerjaan tergolong replikasi parsial dengan perluasan fitur lag. Spark SQL dan MLlib benar-benar dijalankan pada data LCL. '
      'Cakupan tidak meliputi klaster Dataproc, pemetaan blok geografis, pengujian tarif ToU, maupun simulasi energi terbarukan. '
      'Seluruh data lokal berjumlah 168 CSV, 167.932.474 baris, atau 8,54 GB; input eksperimen adalah tiga CSV bernomor 0, 1, dan 2 '
      f'dengan {count(profile["raw_rows"])} rekaman dan {profile["raw_households"]} ID rumah.')
    h('2.2 Lingkungan Perangkat Lunak',2)
    p('Lingkungan dan konfigurasi aktual berasal dari environment.json. Versi pustaka utama dicatat dalam requirements.txt, '
      'sedangkan seluruh dependensi dipin pada requirements-lock.txt. Java 17/21 didukung Spark 4.0.1 '
      '(Apache Software Foundation, 2025a).')
    table('Tabel 1. Lingkungan dan parameter eksperimen (sumber: environment.json).',
          ['Komponen','Konfigurasi tercatat'],[
          ['Platform',env['os']+'; Spark local[2]'],['Python / PySpark',env['python']+' / '+env['spark']],
          ['Java',env['java']],['NumPy / pandas','2.3.3 / 2.3.3'],['Heap / partisi shuffle','4 GB / 8'],
          ['Seed / parsing waktu','42 / UTC sebagai aturan parsing']], [.32,.68])
    h('2.3 Rancangan Variasi Parameter',2)
    p('Sebelas kandidat parameter diuji pada validasi. Data dibagi secara kronologis: latih sebelum September 2013 '
      f'({count(splits["train"])} sampel), validasi September–Oktober ({count(splits["validation"])}), dan uji November–Desember '
      f'({count(splits["test"])}). Parameter dipilih menurut RMSE validasi, kemudian masing-masing keluarga model dilatih ulang '
      'pada gabungan latih–validasi. Uji tidak dipakai menala parameter.')
    table('Tabel 2. Skenario variasi parameter model.', ['Model','Variasi yang diuji','Parameter tetap'],[
          ['MPR','Tanpa penalti','Derajat 2'],['Ridge','regParam 0,001; 0,01; 0,1','Derajat 2; alpha 0'],
          ['Lasso','regParam 0,001; 0,01; 0,1','Derajat 2; alpha 1'],
          ['Elastic Net','regParam 0,001; 0,01','Derajat 2; alpha 0,5'],
          ['Decision tree','maxDepth 5; 12','maxBins 32; minInstances 10']], [.22,.42,.36])

    page();h('2.4 Langkah Eksperimen',2)
    steps=[
      ('Inisialisasi','Membuat SparkSession local[2], menetapkan seed 42 dan skema eksplisit empat kolom; membaca tiga CSV pertama menurut nomor file.'),
      ('Pembersihan','Menghapus spasi, mem-parsing timestamp dan energi dengan fungsi try_*, lalu menolak nilai Null, negatif, waktu invalid, tarif invalid, atau ID kosong. Nol dipertahankan karena tidak ada penanda gangguan meter.'),
      ('Seleksi dan agregasi','Membatasi tahun 2013 serta interval tepat pada menit 00/30. Duplikat ID–tarif–waktu dirata-ratakan. Memilih 50 rumah Std pertama secara leksikografis dengan cakupan minimal 98%; hanya interval lengkap 50 rumah digunakan.'),
      ('Rekayasa fitur','Membentuk sepuluh fitur: sinus–kosinus slot, hari minggu, hari tahun; akhir pekan; lag 30 menit, satu hari, dan satu minggu. Lag memakai join waktu persis, bukan pergeseran nomor baris.'),
      ('Pelatihan dan evaluasi','Menempatkan StandardScaler serta PolynomialExpansion di pipeline regresi. Scaler di-fit pada data pelatihan saja. Menguji RMSE validasi, melatih ulang parameter terpilih, lalu menghitung MSE, RMSE, MAE, R2, dan WAPE pada uji.'),
      ('Penyimpanan dan pemeriksaan','Menyimpan agregat, metrik, parameter, log, serta grafik. verify_results.py menghitung ulang metrik dan memeriksa lag. Dua pengulangan pemodelan dari agregat menghasilkan metrik sama dalam toleransi 1e-12.'),
    ]
    for i,(title,text) in enumerate(steps,1):p(f'<b>{i}. {title}.</b> '+escape(text),markup=True)
    p(f'Input memiliki {profile["null_energy"]} energi Null, {count(profile["zero_energy"])} nol, dan '
      f'{profile["duplicates_collapsed"]} duplikat 2013 yang diringkas. Dari {profile["eligible_households"]} rumah memenuhi cakupan, '
      f'50 dipilih; {profile["incomplete_aggregate_intervals"]} interval tidak lengkap ditolak dan '
      f'{count(profile["complete_aggregate_intervals"])} interval agregat tersisa. Pemilihan berdasarkan kelengkapan tahunan '
      'bersifat retrospektif, sehingga bukan simulasi perekrutan rumah di awal tahun. UTC hanya aturan parsing timestamp tanpa zona.', 'small')
    h('2.5 Perbedaan Dibandingkan dengan Artikel',2)
    table('Tabel 3. Perbandingan cakupan pengujian dengan artikel acuan.',
          ['Aspek','Penelitian asli','Replikasi parsial'],[
          ['Lingkungan','Dataproc multi-node','Windows, local[2]'],
          ['Cakupan rumah','Blok dan seluruh LCL','Kohort 50 rumah Std'],
          ['Fitur tambahan','Cuaca, ACORN, kalender','Kalender serta lag energi'],
          ['Nilai nol','Dihapus pada pembersihan','Dipertahankan'],
          ['Respons tarif','Dianalisis','Tidak diuji']], [.25,.37,.38])

    page();h('III. HASIL PENGUJIAN DAN ANALISIS')
    p('Bagian ini menggunakan keluaran Spark pada results/, bukan angka yang diisi secara manual. Target adalah jumlah energi '
      '50 rumah dalam kWh per 30 menit, bukan daya kW. Evaluasi merupakan rolling satu langkah: observasi terdahulu tersedia '
      'pada tiap waktu ramalan. Seluruh model dibandingkan pada timestamp uji yang sama.')
    h('3.1 Pola Konsumsi Harian dan Bulanan',2)
    table('Tabel 4. Konsumsi menurut jenis hari (sumber: weekend_profile.csv).',
          ['Jenis hari','Rerata kWh/rumah/30 menit','Rekaman'],
          [[x.day_type,num(x.mean_kwh,4),count(x.records)] for x in weekend.itertuples()], [.25,.47,.28])
    picture('descriptive_profiles.png',175,'Gambar 1. Profil menurut jam dan bulan, dihitung dari rekaman kohort valid 2013.')
    p(f'Rerata tertinggi menurut jam muncul pada pukul {int(peak.hour):02d} ({num(peak.mean_kwh)} kWh/rumah/30 menit), '
      f'sedangkan terendah pada pukul {int(low.hour):02d} ({num(low.mean_kwh)}). Rerata akhir pekan berbeda {num(wd,2)}% '
      'terhadap hari kerja. Rerata per jam tetap memakai satuan energi per setengah jam karena menggabungkan dua interval.')
    p(f'Rerata bulan terbesar terdapat pada bulan {int(mh.month)} ({num(mh.mean_kwh)}), dan terkecil pada bulan '
      f'{int(ml.month)} ({num(ml.mean_kwh)} kWh/rumah/30 menit). Pola ini mendukung pemakaian fitur kalender. '
      'Tanpa cuaca, perbedaan tersebut belum dapat diatribusikan kepada suhu. Statistik deskriptif tidak menyatakan efek kausal.')
    p(f'Agregat lengkap mempunyai rerata {num(profile["aggregate_mean_kwh"])} dan maksimum '
      f'{num(profile["aggregate_max_kwh"])} kWh/30 menit. Spark SQL menghitung ringkasan; pandas dan Matplotlib hanya '
      'menerima hasil agregat kecil untuk visualisasi.')

    page();h('3.2 Kinerja Regresi Polinomial dan Regularisasi',2)
    linear=metrics[metrics.model.isin(['MPR','Ridge','Lasso','ElasticNet'])]
    table('Tabel 5. Hasil uji keluarga regresi (sumber: test_metrics.csv).',
          ['Model','regParam','RMSE','MAE','R2','WAPE'],
          [[x.model,num(x.regParam),num(x.RMSE),num(x.MAE),num(x.R2),num(x.WAPE_pct,2)+'%'] for x in linear.itertuples()],
          [.24,.15,.16,.15,.13,.17])
    picture('model_rmse.png',193,'Gambar 2. Perbandingan RMSE model dan baseline pada November–Desember 2013.')
    p(f'MPR mempunyai RMSE uji terendah secara deskriptif, yaitu {num(best.RMSE)}, dengan MAE {num(best.MAE)}, '
      f'R2 {num(best.R2)}, dan WAPE {num(best.WAPE_pct,2)}%. Terhadap persistence, penurunan RMSE sebesar '
      f'{num(improvement,2)}%. R2 dihitung sebagai 1 − SSE/SST; R2 dapat negatif untuk model yang lebih buruk daripada rerata.')
    p('Validasi memilih Ridge 0,001, Lasso 0,01, dan Elastic Net 0,01 dengan alpha 0,5. Di antara keluarga model, '
      'Lasso mempunyai RMSE validasi terendah, 1,256. Urutan MPR pada uji tidak digunakan untuk menala ulang parameter; '
      'selisih regresi yang sangat kecil belum menunjukkan keunggulan stabil antarperiode.')
    p('StandardScaler serta ekspansi polinomial derajat dua menghasilkan 65 komponen dari sepuluh fitur dasar, termasuk '
      'interaksi. Regresi memakai maxIter 200 dan toleransi 1e-7. Parameter regularisasi mengikuti definisi Spark, '
      'sehingga tidak langsung disamakan dengan simbol penalti artikel tanpa menyamakan penskalaan '
      '(Apache Software Foundation, 2025b).')

    page();h('3.3 Kinerja Decision Tree dan Pembanding Sederhana',2)
    dt=trials[trials.model=='DTR']
    table('Tabel 6. Pengaruh kedalaman tree pada validasi (sumber: validation_trials.csv).',
          ['maxDepth','RMSE validasi','R2 validasi','Waktu fit (dtk)'],
          [[int(x.maxDepth),num(x.validation_RMSE),num(x.validation_R2),num(x.fit_seconds)] for x in dt.itertuples()],
          [.20,.28,.26,.26])
    p(f'Kedalaman {configs["DTR"]["maxDepth"]} dipilih oleh validasi. Tree berkedalaman 12 memiliki galat validasi '
      'lebih tinggi daripada tree berkedalaman 5 pada kohort ini; penambahan kedalaman tidak otomatis memperbaiki generalisasi. '
      f'Tree terpilih menghasilkan RMSE uji {num(tree.RMSE)}, MAE {num(tree.MAE)}, dan R2 {num(tree.R2)}.')
    picture('forecast_week.png',185,'Gambar 3. Aktual dan prediksi rolling pada minggu uji pertama; gap menandai interval tanpa baris uji yang memenuhi syarat.')
    baselines=metrics[metrics.model.str.contains('Persistence|Seasonal')]
    p('Baseline memberi RMSE: '+ '; '.join(f'{x.model} = {num(x.RMSE)}' for x in baselines.itertuples())+'. '
      'Semua memakai baris uji yang sama. Model ML menurunkan galat pada periode ini, tetapi kemampuan '
      'ramalan multi-langkah tanpa pembaruan observasi belum diuji.')
    imp=json.loads((r/'tree_importances.json').read_text())
    top=sorted(imp.items(),key=lambda x:x[1],reverse=True)[:3]
    p('Tiga importance tertinggi pada tree ialah '+', '.join(f'{k} ({num(v)})' for k,v in top)+'. '
      'Importance mengukur pengurangan impurity dalam model, bukan hubungan sebab-akibat. '
      'Energi masa lalu berkontribusi besar sehingga ablation tanpa lag merupakan perluasan yang relevan.')

    page();h('3.4 Perbandingan Temuan dengan Artikel',2)
    original={'MPR':(.944,2.472),'Ridge':(.943,2.490),'Lasso':(.943,2.501),'ElasticNet':(.943,2.490),'DTR':(.910,3.215)}
    rows=[]
    for name in original:
        x=metrics[metrics.model==name].iloc[0]
        rows.append([name,num(original[name][0]),num(original[name][1]),num(x.R2),num(x.RMSE)])
    table('Tabel 7. Angka artikel untuk Block #0 dan hasil kohort lokal.',
          ['Model','R2 artikel','RMSE artikel','R2 lokal','RMSE lokal'],rows,[.24,.18,.21,.18,.19])
    p('Angka artikel berasal dari Tabel 6, kolom Block #0; Plain dipetakan ke MPR tanpa penalti. '
      'Artikel dan replikasi menggunakan kohort, fitur, pembersihan, periode, serta protokol berbeda. '
      'Oleh karena itu, RMSE lokal yang lebih rendah tidak membuktikan metode lebih unggul. '
      'R2 lokal yang lebih rendah juga tidak dapat ditafsirkan sebagai reproduksi numerik yang gagal pada kondisi identik '
      '(Ali El-Sayed Ali et al., 2024).')
    p('Pada replikasi, regresi memberikan R2 sekitar 0,86, sedangkan DTR sekitar 0,80. Kecenderungan regresi yang '
      'lebih baik daripada tree dangkal searah dengan angka pembanding. Namun, Lasso terpilih melalui validasi lokal, '
      'sementara artikel merekomendasikan Ridge. Variasi kohort dan penambahan lag dapat mengubah pilihan parameter.')
    p('Elastic Net lokal menguji campuran alpha 0,5; Elastic Net artikel pada blok pembanding berakhir sebagai penalti L2. '
      'Tree lokal dipilih dari kedalaman 5 dan 12, dengan kedalaman 5 terpilih. Ketiga CSV input bukan pemetaan blok: '
      'nomor file 0 tidak berarti Block #0. Baseline serta split waktu dibuat sebagai rancangan replikasi yang dapat diperiksa.')
    p(f'Alur mentah selesai dalam {num(runtime["total_seconds"],2)} detik. Pemodelan dari agregat diulang dengan metrik '
      'sama dalam toleransi 1e-12. Waktu fit dan transformasi yang tersedia hanya pengamatan pada runtime lokal; '
      'tidak digunakan untuk mengklaim skalabilitas klaster. Pengulangan juga tidak menjadi uji signifikansi akurasi, '
      'karena menggunakan data dan seed yang sama.')
    p('MSE adalah rerata galat kuadrat, RMSE akar MSE, MAE rerata galat absolut, dan WAPE adalah jumlah galat absolut '
      'dibagi jumlah energi aktual dikalikan 100%. RMSE serta MAE bersatuan kWh/30 menit; MSE bersatuan kWh kuadrat. '
      'Nilai lengkap dan parameter kandidat disediakan pada Lampiran A.')
    p('Sumber angka artikel:\nhttps://journalofbigdata.springeropen.com/articles/10.1186/s40537-024-00909-6/tables/6','caption')

    page();h('IV. KENDALA DAN REFLEKSI')
    h('4.1 Catatan Pelaksanaan dan Keterbatasan',2)
    p('Kendala yang dicatat meliputi pustaka awal yang belum tersedia, pemasangan pip yang tertahan, serta Java 25 yang '
      'tidak termasuk versi didukung Spark 4.0.1. Dependensi dipasang pada virtual environment; pemasangan diulang dengan '
      '--isolated dan --no-cache-dir, serta JDK Temurin 21 portabel dipakai tanpa mengganti Java global. '
      'Unduhan PowerShell awal gagal; urllib berhasil dan checksum JDK diverifikasi. Catatan ini berasal dari logs/technical_notes.md.')
    p('Keluaran mentah lengkap dihasilkan meskipun pipeline PowerShell awal melaporkan masalah cleanup. '
      'Dua pengulangan model berikutnya keluar dengan kode 0 dan menghasilkan metrik yang sama. Peringatan cleanup '
      'dicatat, bukan disembunyikan sebagai kegagalan yang mengubah hasil.')
    table('Tabel 8. Keterbatasan rancangan dan tindak lanjut.', ['Keterbatasan','Dampak dan tindak lanjut'],[
          ['50 rumah Std; seleksi ID dan cakupan tahunan','Tidak mewakili seluruh LCL; uji kohort lain dan seleksi dari periode latih.'],
          ['Tanpa cuaca, ACORN, dan data tarif rinci','Batasi klaim pada prediksi agregat; tambahkan sumber eksternal bila tersedia.'],
          ['Satu split kronologis; rolling satu langkah','Uji beberapa musim dan horizon multi-langkah.'],
          ['Waktu tanpa zona; duplikat diringkas','Daylight saving belum direkonstruksi; pastikan zona waktu sumber.'],
          ['Kinerja lokal dan sedikit pengulangan','Belum menjadi benchmark; ukur memori/CPU dan ulangi timing terkontrol.']], [.41,.59])
    h('4.2 Refleksi dan Usulan Perbaikan',2)
    p('Eksperimen memperlihatkan pentingnya membedakan replikasi sebagian alur dari reproduksi konfigurasi penuh. '
      'Baseline, validasi berdasarkan waktu, dan pemeriksaan lag diperlukan untuk memberi arti pada metrik. '
      'Hasil yang berbeda dari jurnal tetap dilaporkan. Regularisasi yang paling baik pada validasi tidak harus '
      'menjadi model dengan RMSE uji terkecil, sehingga uji tidak dipakai menala ulang parameter.')
    p('Jika diulang, pekerjaan dapat diperluas dengan validasi rolling lintas musim, beberapa ukuran kohort, ablation lag, '
      'pembersihan nol berdasarkan status meter, serta pengukuran sumber daya yang terkontrol. Usulan tersebut adalah '
      'rencana perbaikan, bukan langkah yang diklaim telah dilakukan.')

    page();h('5. TAUTAN KODE')
    p('Kode, notebook, README, dependensi, agregat, metrik, grafik, dan log disiapkan dalam paket lokal. '
      'Pengguna akan mengunggah sendiri berkas tersebut. Repositori berikut adalah tujuan unggah; isi lengkap eksperimen '
      'belum dipublikasikan otomatis dan akses seluruh berkas perlu diperiksa setelah unggahan manual.')
    p(f'Tautan repositori tujuan: <link href="{escape(repo_url)}">{escape(repo_url)}</link>',markup=True)
    p('Pemodelan dapat diulang tanpa CSV besar menggunakan perintah berikut, setelah Java 17/21 dan dependensi tersedia. '
      'Cara mengulangi praproses mentah serta sumber unduhan dijelaskan pada README.','small')
    p('python src/experiment.py --aggregate results/aggregate_2013.csv\npython src/make_report.py','code')
    h('DAFTAR PUSTAKA')
    refs=[
      'Ali El-Sayed Ali, H., Alham, M. H., &amp; Ibrahim, D. K. (2024). Big data resolving using Apache Spark for load forecasting and demand response in smart grid: A case study of Low Carbon London Project. <i>Journal of Big Data, 11</i>, Article 59. '+paper,
      'Apache Software Foundation. (2025a). <i>Overview: Spark 4.0.1 documentation.</i> https://spark.apache.org/docs/4.0.1/',
      'Apache Software Foundation. (2025b). <i>LinearRegression: PySpark 4.0.1 documentation.</i> https://spark.apache.org/docs/4.0.1/api/python/reference/api/pyspark.ml.regression.LinearRegression.html',
      'Apache Software Foundation. (2025c). <i>DecisionTreeRegressor: PySpark 4.0.1 documentation.</i> https://spark.apache.org/docs/4.0.1/api/python/reference/api/pyspark.ml.regression.DecisionTreeRegressor.html',
      'SCImago. (n.d.). <i>SJR: Journal rankings on Information Systems</i> [Data 2024]. Diakses 14 Oktober 2026, dari https://www.scimagojr.com/journalrank.php?area=1700&amp;category=1710&amp;openaccess=true&amp;type=j',
      'Springer Nature. (n.d.). <i>Journal of Big Data: Journal information.</i> Diakses 14 Oktober 2026, dari https://link.springer.com/journal/40537',
      'UK Power Networks. (2022). <i>SmartMeter energy consumption data in London households</i> [Data set; pembaruan 7 April 2022]. London Datastore. '+data,
    ]
    for ref in refs:p(ref.replace(' https://','<br/>https://'),'ref',markup=True)
    h('PERNYATAAN PENGGUNAAN ALAT BANTU')
    p('OpenAI Codex membantu membaca panduan, memverifikasi sumber, merancang dan menulis kode, menjalankan '
      'pengujian, membuat grafik, serta menyusun laporan dan menyesuaikan strukturnya dengan contoh pengguna. '
      'Angka berasal dari eksekusi nyata. Penggunaan AI mengikuti izin dosen; mahasiswa bertanggung jawab '
      'memeriksa hasil dan memahami kode. Tidak ada klaim pekerjaan tanpa bantuan AI.','small')

    page();h('LAMPIRAN A. DATA PENGUJIAN PER KONFIGURASI')
    p('Lampiran menyajikan keluaran per kandidat validasi dan seluruh model uji. Durasi fit dan transformasi adalah '
      'pengukuran aktual pada eksekusi awal; bukan rerata benchmark. Baris uji model berjumlah '+count(splits['test'])+'.')
    rows=[]
    for x in trials.itertuples():
        conf='depth '+str(int(x.maxDepth)) if x.model=='DTR' else 'reg '+num(x.regParam)+'; a '+num(x.elasticNetParam,1)
        rows.append([x.model,conf,num(x.validation_RMSE),num(x.validation_R2),num(x.fit_seconds),num(x.predict_seconds)])
    table('Tabel A.1. Kandidat validasi dari validation_trials.csv.',
          ['Model','Konfigurasi','RMSE val.','R2 val.','Fit (dtk)','Pred. (dtk)'],rows,[.17,.29,.15,.13,.13,.13])
    p('Konfigurasi dengan RMSE validasi terkecil di setiap keluarga dilatih ulang pada latih–validasi. '
      'Waktu prediksi mencakup transformasi Spark, pengurutan, dan pengambilan keluaran ke driver.','small')
    rows=[[x.model,num(x.MSE),num(x.RMSE),num(x.MAE),num(x.R2),num(x.WAPE_pct,2)+'%'] for x in metrics.itertuples()]
    table('Tabel A.2. Metrik seluruh model dari test_metrics.csv.', ['Model','MSE','RMSE','MAE','R2','WAPE'],rows,[.31,.14,.14,.14,.12,.15])
    p('Baseline tidak melakukan pelatihan. Metrik model yang diulang dari agregat sama dalam toleransi 1e-12; '
      'hasil pemeriksaan ada pada verification.json dan reproducibility_check.json.','small')
    def footer(c,doc):
        if doc.page>1:
            c.saveState();c.setFont(font,9);c.drawCentredString(A4[0]/2,12*mm,str(doc.page-1));c.restoreState()
    doc=SimpleDocTemplate(str(output),pagesize=A4,leftMargin=left,rightMargin=right,
                          topMargin=21*mm,bottomMargin=21.5*mm,title='Replikasi Parsial Prediksi Beban Listrik Low Carbon London',
                          author='Ray Regan Sitepu',subject='Eksplorasi Mahadata IF25-40402; struktur sesuai contoh pengguna')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    (d/'Laporan_Eksplorasi_Mahadata.md').write_text('\n'.join(md),encoding='utf-8')
    notebook_builder()
    print(output)
