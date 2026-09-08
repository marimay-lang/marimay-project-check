#!/usr/bin/env python3
"""Project-owned policy oracle, using only synthetic files and configurations."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from mmay_acceptance import Application
ROOT=Path(__file__).resolve().parents[1]
APP=Application(ROOT,timeout=180)
WORK=ROOT/'build'/'acceptance'; WORK.mkdir(parents=True,exist_ok=True)
TREE=ROOT.parent/'.acceptance-data'/ROOT.name/'дерево'
if TREE.exists(): shutil.rmtree(TREE)
TREE.mkdir(parents=True)
CONFIG=WORK/'config.json'
started=time.monotonic()
engines=APP.engines(WORK,'app',['--allow-read',str(WORK),'--allow-read',str(TREE),'--max-heap-bytes','67108864'])
cases=[]
def encoded(value): return json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()
def configuration(**updates):
    value={'version':2,'project':{'name':'пример','root':str(TREE)},'scan':{'extensions':['.my'],'maxFileBytes':3,'requiredFiles':[]}}
    value['scan'].update(updates)
    return value
current=configuration()
def case(value=None,flags=(),status=0,output=b'',error=None,selected=None):
    payload=encoded(current if value is None else value) if not isinstance(value,bytes) else value
    CONFIG.write_bytes(payload)
    def check(engine,result):
        assert result.stdout==output,(engine,result.stdout[:1500],output[:1500])
        if error is None: assert not result.stderr,(engine,result.stderr)
        else: assert result.stderr.startswith(b'marimay-project-check: ') and error.encode() in result.stderr,(engine,result.stderr,error)
        assert CONFIG.read_bytes()==payload,'configuration changed'
    args=[str(CONFIG),*flags]
    result=APP.compare(engines if selected is None else selected,args,status,verify=check)
    cases.append({'arguments':args,'config':payload.decode('utf-8',errors='backslashreplace'),'status':status,'stdout_sha256':hashlib.sha256(output).hexdigest(),'stderr':result[2].decode()})
def report(findings): return encoded({'project':'пример','ok':not findings,'findings':findings})+b'\n'
case(output='пример: OK\n'.encode())
case(flags=['--json'],output=report([]))
case(flags=['--max-entries','0'],output='пример: OK\n'.encode())
(TREE/'а.my').write_bytes(b'abc'); (TREE/'dir').mkdir(); (TREE/'dir'/'б.my').write_bytes(b'')
case(configuration(requiredFiles=['а.my','dir/б.my']),['--json'],output=report([]))
(TREE/'a.txt').write_bytes(b'abcd')
findings=[{'path':'a.txt','code':'extension','message':'Расширение не разрешено'}, {'path':'a.txt','code':'size','message':'Размер 4 превышает 3 байт'}, {'path':'missing.my','code':'missing','message':'Обязательный файл отсутствует'}, {'path':'dir','code':'required-kind','message':'Обязательная запись должна быть обычным файлом'}]
case(configuration(requiredFiles=['missing.my','dir']),['--json'],1,report(findings))
case(configuration(requiredFiles=['missing.my','dir']),status=1,output=''.join(f"{f['path']}: {f['code']}: {f['message']}\n" for f in findings).encode())
case(configuration(extensions=[],maxFileBytes=4),['--json'],output=report([]))
old={'version':1,'name':'пример','root':str(TREE),'extensions':[],'maxFileBytes':4}
case(old,['--json'],output=report([]))
# Strict configuration and additional project-root containment rules.
for value,error in [(b'{','Ошибка JSON'),(b'\xff','not valid UTF-8'),(b'{"version":2,"version":2}','duplicate JSON field'),(dict(current,unknown=1),'unknown JSON field'),(dict(current,version=3),'Неподдерживаемая версия'),(configuration(maxFileBytes=0),'от 1 до 67108864'),(configuration(extensions=['.my','.my']),'повторяющееся расширение'),(configuration(requiredFiles=['a','a']),'повторяющийся обязательный файл'),(configuration(requiredFiles=['../outside']),'внутри корня'),(configuration(requiredFiles=['dir/../а.my']),'внутри корня')]:
    case(value,['--json'],2,error=error)
for flags,error in [(['--max-entries','1'],'Превышен лимит'),(['--max-depth','0'],'Превышена глубина'),(['--max-entries','65537'],'допустимо 0..65536'),(['--max-depth','-1'],'допустимо 0..256'),(['--max-depth','x'],'ожидается целое число'),(['--unknown'],'unknown option')]:
    case(flags=flags,status=2,error=error)
missing=dict(current,project={'name':'пример','root':str(TREE/'missing')})
case(missing,status=2,error='filesystem path was not found')
file_root=dict(current,project={'name':'пример','root':str(TREE/'а.my')})
case(file_root,status=2,error='Корень должен быть каталогом')
# Capability denial is tested separately from host filesystem permissions.
denied=WORK/'denied'
APP.successful([APP.compiler,'build','.','--release','--output',str(denied),'--allow-read',str(WORK)])
case(flags=['--json'],status=2,error='fs.read capability denied',selected={'vm':[APP.compiler,'run','.','--allow-read',str(WORK),'--'],'release':[str(denied)]})
pipes=[]
if os.name!='nt':
    (TREE/'link').symlink_to(TREE/'dir')
    case(configuration(extensions=[],maxFileBytes=4),['--json'],1,report([{'path':'link','code':'kind','message':'Недопустимый тип записи: symlink'}]))
    (TREE/'link').unlink()
    if os.geteuid()!=0:
        (TREE/'locked').mkdir(); (TREE/'locked'/'hidden.my').write_bytes(b'')
        (TREE/'locked').chmod(0)
        try:
            expected=[{'path':'locked','code':'read','message':'directory enumeration failed'}, {'path':'locked/hidden.my','code':'unverified','message':'Наличие файла не подтверждено: обход неполон'}]
            case(configuration(extensions=[],maxFileBytes=4,requiredFiles=['locked/hidden.my']),['--json'],1,report(expected))
        finally: (TREE/'locked').chmod(0o700)
        shutil.rmtree(TREE/'locked')
    CONFIG.write_bytes(encoded(configuration(extensions=[],maxFileBytes=4)))
    for engine,prefix in engines.items():
        r,w=os.pipe(); os.close(r)
        try: child=subprocess.Popen([*prefix,str(CONFIG),'--json'],cwd=ROOT,stdout=w,stderr=subprocess.PIPE)
        finally: os.close(w)
        _,error=child.communicate(timeout=180)
        assert child.returncode==2 and (b'standard stream write failed' in error or b'standard stream flush failed' in error),(engine,child.returncode,error)
        pipes.append({'engine':engine,'status':child.returncode,'stderr':error.decode()})
# Wider input yields every independent finding, rather than first-error exit.
(TREE/'a.txt').unlink()
for index in range(511,-1,-1): (TREE/f'wide-{index:04d}.bad').write_bytes(b'abcd')
wide=[]
for index in range(512):
    name=f'wide-{index:04d}.bad'
    wide.extend([{'path':name,'code':'extension','message':'Расширение не разрешено'},{'path':name,'code':'size','message':'Размер 4 превышает 3 байт'}])
case(flags=['--json'],status=1,output=report(wide))
help_result=APP.compare(engines,['--help'],0,verify=lambda e,r:None if not r.stderr and b'marimay-project-check' in r.stdout else (_ for _ in ()).throw(AssertionError(r)))
cases.append({'arguments':['--help'],'status':0,'stdout_sha256':hashlib.sha256(help_result[1]).hexdigest()})
result={'schema':'marimay-project-check.acceptance/1','harness':APP.metadata(engines),'cases':cases,'closed_pipes':pipes,'wide_findings':len(wide),'elapsed_seconds':time.monotonic()-started}
(WORK/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(f'project-check: {len(cases)} exact VM/native cases, {len(pipes)} pipes, {len(wide)} findings')
