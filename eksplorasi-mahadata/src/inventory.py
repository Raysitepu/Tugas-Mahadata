"""Inventaris read-only seluruh CSV LCL; hitung baris tanpa memuat 8,54 GB ke RAM."""
import argparse
import json
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--data-dir',required=True);p.add_argument('--output',default='results/full_inventory.json')
    args=p.parse_args()
    files=sorted(Path(args.data_dir).glob('LCL-June2015v2_*.csv'),key=lambda f:int(f.stem.rsplit('_',1)[1]))
    records=[]
    for f in files:
        count=0;last=b''
        with f.open('rb') as stream:
            header=stream.readline().decode('utf-8-sig').strip()
            while True:
                block=stream.read(8*1024*1024)
                if not block:break
                count+=block.count(b'\n');last=block[-1:]
        records.append({'file':f.name,'bytes':f.stat().st_size,'rows':count+int(bool(last) and last!=b'\n'),'header':header})
    out={'files':len(records),'total_rows':sum(r['rows'] for r in records),'total_bytes':sum(r['bytes'] for r in records),
         'method':'count data lines; assumes one record per CSV line; no dataset mutation','records':records}
    dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(out,indent=2),encoding='utf-8')
    print({k:v for k,v in out.items() if k!='records'})

if __name__=='__main__':main()
