"""Bangun grafik dan PDF 10 halaman dari keluaran eksperimen yang benar-benar ada."""
import argparse
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
from xml.sax.saxutils import escape

os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[1]/'tmp'/'matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether

ROOT = Path(__file__).resolve().parents[1]
R = ROOT/'results'
D = ROOT/'docs'
PAPER = 'https://doi.org/10.1186/s40537-024-00909-6'
DATA = 'https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d'
TITLE = 'Replikasi Parsial Prediksi Beban Listrik Low Carbon London Menggunakan Apache Spark'
FILE = '123140047_Ray-Regan-Sitepu_Eksplorasi-Mahadata.pdf'


def plots():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,
                         'axes.spines.top':False,'axes.spines.right':False,
                         'axes.titleweight':'bold','figure.dpi':150})
    h=pd.read_csv(R/'hourly_profile.csv')
    m=pd.read_csv(R/'monthly_profile.csv')
    t=pd.read_csv(R/'test_metrics.csv')
    p=pd.read_csv(R/'test_predictions.csv',parse_dates=['timestamp'])
    fig,axs=plt.subplots(1,2,figsize=(9,3.1),layout='constrained')
    axs[0].plot(h.hour,h.mean_kwh,'o-',color='#176B87',ms=3)
    axs[0].set(xlabel='Jam pencatatan',ylabel='kWh/rumah/30 menit',title='Profil rata-rata menurut jam',xticks=[0,4,8,12,16,20,23])
    axs[1].plot(m.month,m.mean_kwh,'o-',color='#D08A36',ms=3)
    axs[1].set(xlabel='Bulan 2013',ylabel='kWh/rumah/30 menit',title='Profil rata-rata menurut bulan',xticks=range(1,13))
    for ax in axs: ax.grid(alpha=.2)
    fig.savefig(R/'descriptive_profiles.png',dpi=190);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,3.1),layout='constrained')
    t=t.sort_values('RMSE',ascending=False)
    palette=['#8E9DA7' if 'Seasonal' in s or 'Persistence' in s else '#176B87' for s in t.model]
    ax.barh(t.model,t.RMSE,color=palette)
    for i,v in enumerate(t.RMSE):ax.text(v+.035,i,f'{v:.3f}',va='center',fontsize=9)
    ax.set(xlabel='RMSE (kWh per 30 menit, agregat 50 rumah)',title='Galat pada data uji November-Desember')
    ax.set_xlim(0,t.RMSE.max()*1.17);ax.grid(axis='x',alpha=.2)
    fig.savefig(R/'model_rmse.png',dpi=190);plt.close(fig)
    ml=t[t.model.isin(['MPR','Ridge','Lasso','ElasticNet','DTR'])].sort_values('RMSE').iloc[0]['model']
    first=p.timestamp.min().normalize()
    week=p[(p.timestamp>=first)&(p.timestamp<first+pd.Timedelta(days=7))]
    # Gaps must be visible instead of joining points across missing test intervals.
    week=week.set_index('timestamp').reindex(pd.date_range(first,periods=7*48,freq='30min'))
    week.index.name='timestamp';week=week.reset_index()
    fig,ax=plt.subplots(figsize=(9,3.4),layout='constrained')
    ax.plot(week.timestamp,week.energy,label='Aktual',color='#172D3D',lw=1.5)
    ax.plot(week.timestamp,week[ml],label=ml,color='#C67832',lw=1.1,alpha=.9)
    ax.plot(week.timestamp,week['DTR'],label='DTR',color='#77808A',lw=.9,alpha=.85,linestyle='--')
    ax.set(ylabel='kWh/30 menit (50 rumah)',xlabel='Tanggal November 2013',title='Prediksi rolling 30 menit pada minggu uji pertama')
    ax.legend(ncol=3,frameon=False);ax.grid(alpha=.2)
    fig.savefig(R/'forecast_week.png',dpi=190);plt.close(fig)
    return ml


def notebook():
    payload=base64.b64encode(gzip.compress((R/'aggregate_2013.csv').read_bytes())).decode()
    digest=hashlib.sha256((R/'aggregate_2013.csv').read_bytes()).hexdigest()
    script=(ROOT/'src/experiment.py').read_text(encoding='utf-8')
    script=script.rsplit("if __name__=='__main__':",1)[0]
    cells=[]
    def md(s): cells.append({'cell_type':'markdown','metadata':{},'source':s.splitlines(True)})
    def code(s): cells.append({'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':s.splitlines(True)})
    md(f'# {TITLE}\n**Ray Regan Sitepu | 123140047 | R**\n\nArtikel: {PAPER}\n\n'
       'Notebook ini memuat agregat 50 rumah dan implementasi Spark, sehingga pemodelan dapat diulang '
       'tanpa mengunduh 8,54 GB CSV mentah. Jalankan sel secara berurutan pada kernel Python dengan Java 17/21. '
       'Sel notebook belum dieksekusi sebagai notebook; hasil acuan berasal dari skrip eksperimen yang benar-benar dijalankan. '
       'Untuk mengulang pembersihan data mentah, gunakan paket repositori dan README.\n\n'
       f'Sumber data: UK Power Networks, London Datastore, Creative Commons Attribution: {DATA}. '
       'Kode dan laporan dibantu OpenAI Codex; ikuti ketentuan dosen mengenai bantuan AI.')
    code('%pip install pyspark==4.0.1 pandas==2.3.3 numpy==2.3.3 matplotlib==3.10.7')
    md('## 1. Pulihkan data agregat dan verifikasi integritas\nData ini dihasilkan oleh Spark dari tiga partisi CSV pertama, '
       '50 rumah Std dengan cakupan tahunan >=98%. SHA-256 memastikan data tertanam sama dengan hasil eksperimen.')
    profile=json.loads((R/'profile.json').read_text())
    # The portable notebook carries aggregate metadata, without individual IDs.
    profile.pop('cohort_ids',None)
    code("from pathlib import Path\nimport base64, gzip, hashlib, json\nwork = Path('lcl_notebook_run').resolve()\n"
         "(work/'results').mkdir(parents=True, exist_ok=True)\n"
         f"raw = gzip.decompress(base64.b64decode({payload!r}))\nassert hashlib.sha256(raw).hexdigest() == {digest!r}\n"
         "(work/'results/aggregate_2013.csv').write_bytes(raw)\n"
         f"(work/'results/profile.json').write_text(json.dumps({profile!r}, indent=2))\n"
         "import pandas as pd\npd.read_csv(work/'results/aggregate_2013.csv').head()")
    md('## 2. Implementasi Spark yang sama dengan eksperimen\nPipeline memakai split waktu, lag waktu persis, '
       'standardisasi di dalam model, pemilihan parameter di validasi, dan evaluasi rolling satu langkah. '
       'Fungsi `run()` juga mendukung CSV mentah jika argumen `aggregate` dihilangkan.')
    code(script)
    md('## 3. Jalankan ulang pemodelan\nWaktu eksekusi dapat berbeda menurut lingkungan. '
       'Uji November-Desember tidak digunakan dalam pemilihan parameter. Agregat disediakan lengkap; '
       'lag hanya memakai nilai yang tersedia sebelum waktu prediksi.')
    code("from argparse import Namespace\nargs = Namespace(output=str(work), aggregate=str(work/'results/aggregate_2013.csv'),\n"
         "    data_dir='', files=3, households=50, min_coverage=0.98, master='local[2]')\n"
         "hasil = run(args)\nhasil")
    md('## 4. Grafik dan interpretasi\nBandingkan setiap model dengan baseline dan angka jurnal. '
       'Angka jurnal memiliki kohort, fitur, dan protokol berbeda; tidak menunjukkan eksperimen ini lebih unggul.')
    code("import matplotlib.pyplot as plt\nhasil.sort_values('RMSE').plot.barh(x='model', y='RMSE', legend=False)\n"
         "plt.xlabel('RMSE (kWh/30 menit, 50 rumah)')\nplt.show()\n"
         "pred = pd.read_csv(work/'results/test_predictions.csv', parse_dates=['timestamp'])\n"
         "pred.set_index('timestamp')[['energy','Ridge']].iloc[:336].plot(figsize=(12,4))\nplt.show()")
    md('## Hasil acuan yang sudah diverifikasi\nTabel berikut disalin dari keluaran skrip eksperimen, '
       'bukan hasil yang diklaim telah dieksekusi dalam notebook ini.\n\n'+pd.read_csv(R/'test_metrics.csv').round(5).to_csv(index=False))
    for i,cell in enumerate(cells):cell['id']=f'lcl-{i:02}'
    nb={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
        'language_info':{'name':'python','version':'3.13'}},'nbformat':4,'nbformat_minor':5}
    (ROOT/'Eksplorasi_Mahadata.ipynb').write_text(json.dumps(nb,ensure_ascii=False,indent=1),encoding='utf-8')


def build(repo_url='https://github.com/Raysitepu/Tugas-Mahadata'):
    from report_layout import build_report
    return build_report(ROOT, repo_url, plots, notebook)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo-url',default='https://github.com/Raysitepu/Tugas-Mahadata')
    build(p.parse_args().repo_url)
