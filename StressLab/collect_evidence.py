"""Optional bounded experiment collector. Run from the project directory."""
import json
import platform
import time
from pathlib import Path
from engine import Engine

if __name__ == '__main__':
    out=Path('evidence');out.mkdir(exist_ok=True)
    engine=Engine()
    experiments=[]
    try:
        for name, settings in [
            ('cpu-low',dict(workers=1,memory_mib=0,duration=5,level='Low')),
            ('cpu-medium',dict(workers=1,memory_mib=0,duration=5,level='Medium')),
            ('cpu-high',dict(workers=1,memory_mib=0,duration=5,level='High',confirm_high=True)),
            ('memory-32',dict(workers=0,memory_mib=32,duration=5,level='Low'))]:
            engine.start(settings)
            while engine.snapshot()['status'] in ('Baseline','Running','Stopping','Recovery'):
                time.sleep(.2)
            snapshot=engine.snapshot()
            (out/(name+'.csv')).write_text(engine.csv_text(),encoding='utf-8')
            experiments.append(dict(name=name,**snapshot['summary']))
            print(name,snapshot['status'],flush=True)
        result=dict(environment=platform.platform(),note='Actual measurements in a shared Linux execution environment, not the student Windows laptop. System metrics include unrelated activity. No benchmark or accuracy claim.',experiments=experiments)
        (out/'measurements.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    finally:engine.close()
