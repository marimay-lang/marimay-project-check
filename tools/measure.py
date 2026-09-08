#!/usr/bin/env python3
"""Sequential measurements against predeclared budgets and independent outputs."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import time
from mmay_acceptance import Application
ROOT=Path(__file__).resolve().parents[1]
APP=Application(ROOT,timeout=240)
NAME=ROOT.name.removeprefix('marimay-')
STAMP=str(time.time_ns())
WORK=ROOT/'build'/('measure-'+STAMP); WORK.mkdir(parents=True)
DATA=ROOT.parent/'.measure-data'/ROOT.name/STAMP; DATA.mkdir(parents=True)
records=[]; datasets=[]
def encoded(value): return json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()+b'\n'
def file_dataset(count,directories):
    directory=DATA/str(count); directory.mkdir()
    rows=[]
    for d in range(directories):
        folder=directory/f'dir-{d:03d}'; folder.mkdir()
        rows.append({'path':folder.name,'kind':'directory','size':0})
    for index in range(count):
        relative=f'dir-{index%directories:03d}/файл-{index:05d}.my'
        contents=b'x'*(index%64)
        (directory/relative).write_bytes(contents)
        rows.append({'path':relative,'kind':'file','size':len(contents)})
    if NAME=='manifest':
        args=['generate',str(directory),'--max-entries','20000']
        expected=encoded({'version':1,'entries':sorted(rows,key=lambda row:row['path'].encode())})
    else:
        configuration={'version':2,'project':{'name':'измерение','root':str(directory)},'scan':{'extensions':['.my'],'maxFileBytes':63,'requiredFiles':[]}}
        source=DATA/f'config-{count}.json'; source.write_bytes(encoded(configuration))
        args=[str(source),'--json','--max-entries','20000']
        expected=encoded({'project':'измерение','ok':True,'findings':[]})
    return {'name':f'{count}-files','arguments':args,'status':0,'output':expected,'files':count,'directories':directories,'inventory_sha256':hashlib.sha256(encoded(rows)).hexdigest()}
grants=['--max-heap-bytes','67108864']
if NAME!='env-paths':
    grants.extend(['--allow-read',str(DATA)])
    datasets=[file_dataset(1,1),file_dataset(1000,20),file_dataset(10000,100)]
else:
    args=[]; variables=[]; paths=[]
    for index in range(100):
        name=f'MMAY_FILE_MEASURE_{index:03d}'
        os.environ[name]=f'значение-{index}'
        args.extend(['--env',name])
        if index<64:
            grants.extend(['--allow-env',name]); variables.append({'name':name,'state':'present','value':os.environ[name],'error':''})
        else:
            variables.append({'name':name,'state':'error','value':'','error':f'environment variable {name} is not allowed'})
    for index in range(100):
        value=f'папка-{index}/../file-{index}'
        args.extend(['--path',value]); paths.append({'input':value,'normalized':f'file-{index}','absolute':False,'error':''})
    datasets=[{'name':'small','arguments':['--path','a/../б'],'status':0,'output':encoded({'ok':True,'context':False,'directory':'','variables':[],'paths':[{'input':'a/../б','normalized':'б','absolute':False,'error':''}]})},
              {'name':'100-env-100-paths','arguments':args,'status':1,'output':encoded({'ok':False,'context':False,'directory':'','variables':variables,'paths':paths})}]
binary=WORK/'app-release'
APP.successful([APP.compiler,'build','.',*grants,'--release','--output',str(binary)])
engines={'native':[str(binary)],'vm':[APP.compiler,'run','.',*grants,'--']}
def measured(engine,dataset,repetition,budget):
    command=[*engines[engine],*dataset['arguments']]
    timing=['/usr/bin/time','-l' if platform.system()=='Darwin' else '-v'] if platform.system() in ('Darwin','Linux') else []
    started=time.monotonic(); result=APP.run([*timing,*command]); seconds=time.monotonic()-started
    assert (result.returncode,result.stdout)==(dataset['status'],dataset['output']),(engine,dataset['name'],result.returncode,result.stdout[:1000],result.stderr[:1000])
    rss=None
    if platform.system()=='Darwin':
        found=re.search(rb'^\s*(\d+)\s+maximum resident set size\s*$',result.stderr,re.M)
        if found: rss=int(found[1])
    elif platform.system()=='Linux':
        found=re.search(rb'Maximum resident set size \(kbytes\):\s*(\d+)',result.stderr)
        if found: rss=int(found[1])*1024
    rss_budget=(128 if engine=='native' else 256)*1024*1024
    records.append({'engine':engine,'dataset':dataset['name'],'repetition':repetition,'command':command,'seconds':seconds,'seconds_budget':budget,'within_time_budget':seconds<=budget,'rss_bytes':rss,'rss_budget':rss_budget,'within_rss_budget':None if rss is None else rss<=rss_budget,'stdout_sha256':hashlib.sha256(result.stdout).hexdigest(),'timing_stderr':result.stderr.decode()})
    print(NAME,engine,dataset['name'],repetition,round(seconds,4),rss,flush=True)
# No application process is run between the build above and this first sample.
for engine in engines:
    for repetition in range(4): measured(engine,datasets[0],repetition,0.1 if engine=='native' else 0.5)
for dataset in datasets[1:]:
    for engine in engines:
        budget=(0.1 if engine=='native' else 0.5) if NAME=='env-paths' else ((20 if engine=='native' else 200) if dataset['files']==10000 else (2 if engine=='native' else 20))
        for repetition in range(3 if NAME=='env-paths' or dataset['files']==1000 else 1): measured(engine,dataset,repetition,budget)
APP.successful([APP.compiler,'test','.','--engine','both'])
started=time.monotonic(); tests=APP.successful([APP.compiler,'test','.','--engine','both']); test_seconds=time.monotonic()-started
report={'schema':ROOT.name+'.measurements/1','host':platform.platform(),'harness':APP.metadata(engines),'conditions':'Sequential after compiler verification; ordinary desktop background, no OS cache eviction. First execution of this produced artifact follows build; not a disk-cold or fresh-host claim.','sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.rglob('*.my')) if '.mmay' not in p.parts and 'build' not in p.parts},'budgets_sha256':hashlib.sha256((ROOT/'BUDGETS.md').read_bytes()).hexdigest(),'datasets':[{**{k:v for k,v in data.items() if k!='output'},'output_sha256':hashlib.sha256(data['output']).hexdigest()} for data in datasets],'records':records,'test_both':{'seconds':test_seconds,'seconds_budget':2,'within_budget':test_seconds<=2,'stdout':tests.decode()}}
(WORK/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(ROOT/'build/latest-measurement.txt').write_text(str(WORK/'report.json')+'\n')
print(WORK/'report.json')
