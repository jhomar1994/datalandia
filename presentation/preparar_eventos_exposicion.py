"""Genera archivos locales para la exposición. NO publica ni inicia GCP."""
import argparse,json,uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--out',type=Path,default=ROOT/'referencias_locales/exposicion')
 args=p.parse_args()
 if args.out.exists():p.error('Usar otra carpeta --out para no sobrescribir una sesión previa')
 source=ROOT/'data/p3/input/sensores.jsonl'
 if not source.is_file():p.error('Falta el bundle de datos P3 preparado en data/p3/input')
 with source.open() as f:base=json.loads(next(f))
 args.out.mkdir(parents=True)
 session='expo-'+uuid.uuid4().hex
 warm=dict(base,event_id=session+'-warmup',value=10.0)
 (args.out/'warmup.jsonl').write_text(json.dumps(warm)+'\n')
 rows=[]
 for i in range(60):
  rows.append(dict(base,event_id=session+f'-{i:02}',value=10+i/10))
  if i in (15,40):rows.append(dict(base,event_id=session+f'-invalid-{i}',value='error'))
 (args.out/'eventos.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
 print(json.dumps({'folder':str(args.out),'warmup_id':warm['event_id'],'messages':len(rows),'valid':60,'invalid':2},indent=2))

if __name__=='__main__':main()
