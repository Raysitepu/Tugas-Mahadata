"""Siapkan ZIP lokal untuk unggahan manual; hanya data agregat disertakan."""
import json
import re
import zipfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
out=root.parent/'output'
out.mkdir(exist_ok=True)
dest=out/'123140047_Ray-Regan-Sitepu_Paket-Mahadata.zip'
included=[]
sources=[root/'.gitignore',root/'README.md',root/'requirements.txt',root/'requirements-lock.txt',
         root/'run.ps1',root/'Eksplorasi_Mahadata.ipynb']
for folder in ('src','docs','assets','results','logs'):
    sources.extend(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
    for p in sorted(set(sources)):
        relative=p.relative_to(root).as_posix()
        if relative=='results/household_coverage.csv':continue
        if p.suffix.lower()=='.pdf':continue
        blob=p.read_bytes()
        if relative=='results/profile.json':
            profile=json.loads(blob)
            profile.pop('cohort_ids',None)
            profile['release_note']='Aggregate-only release; individual cohort identifiers omitted.'
            blob=json.dumps(profile,indent=2).encode('utf-8')
        if p.suffix in ('.json','.csv','.py','.md','.txt','.log','.ipynb','.ps1'):
            assert not re.search(rb'MAC\d{6}',blob),f'Individual identifier found in release: {relative}'
        z.writestr(relative,blob)
        included.append(relative)
    info={'files':included,'upload':'manual by user','individual_household_coverage_included':False,
          'cohort_identifiers_included':False,'raw_csv_included':False,'git_history_included':False}
    z.writestr('RELEASE_MANIFEST.json',json.dumps(info,indent=2))
with zipfile.ZipFile(dest) as z:assert z.testzip() is None
print(dest)
print('Release files:',len(included)+1,'ZIP bytes:',dest.stat().st_size)
