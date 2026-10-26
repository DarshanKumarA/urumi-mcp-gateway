"""Disposable Docker-only acceptance; never uses Kubernetes or real credentials."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from uuid import uuid4


def run(*args,check=True):
    result=subprocess.run(args,capture_output=True,text=True,encoding='utf-8')
    if check and result.returncode: raise RuntimeError('Fixture operation failed: '+args[0])
    return result.stdout.strip()
def request(url):
    try:
        with urlopen(url,timeout=3) as r: return r.status,r.read().decode(),dict(r.headers)
    except HTTPError as e: return e.code,e.read().decode(),dict(e.headers)
def wait(url,status):
    for _ in range(60):
        try:
            if request(url)[0]==status:return
        except Exception: pass
        time.sleep(.5)
    raise RuntimeError('Listener did not become available')
def security(name,python=True):
    spec=json.loads(run('docker','inspect',name))[0]
    assert spec['Config']['User']=='10001:10001'
    assert spec['HostConfig']['ReadonlyRootfs']
    assert spec['HostConfig']['CapDrop']==['ALL']
    assert 'no-new-privileges:true' in spec['HostConfig']['SecurityOpt']
    proc=run('docker','exec',name,'cat','/proc/1/status')
    assert re.search(r'CapEff:\s+0000000000000000',proc)
    assert re.search(r'NoNewPrivs:\s+1',proc) and re.search(r'Seccomp:\s+2',proc)
    assert re.search(r'Uid:\s+10001\s+10001',proc) and re.search(r'Gid:\s+10001\s+10001',proc)
    if python:
        run('docker','exec',name,'python','-m','pip','check')
        run('docker','exec',name,'python','-c',
            "import errno, pathlib\ntry: pathlib.Path('/tmp/blocked').write_text('fixture')\nexcept OSError as e: assert e.errno == errno.EROFS\nelse: raise AssertionError('Writable root')")
    print('PASS security',name.split('-')[0], '10001:10001/read-only/CapEff=0/NoNewPrivs=1/Seccomp=2')

def main():
    suffix=uuid4().hex[:10];network='urumi-stage71-'+suffix
    db='stage71-db-'+suffix;gateway='gateway-'+suffix;dashboard='dashboard-'+suffix
    containers=[]
    with tempfile.TemporaryDirectory(prefix='urumi-stage71-container-') as folder:
        try:
            run('docker','network','create',network)
            run('docker','run','-d','--name',db,'--network',network,'--network-alias','stage71-db',
                '-e','POSTGRES_HOST_AUTH_METHOD=trust','-e','POSTGRES_USER=fixture','-e','POSTGRES_DB=urumi_gateway_fixture',
                '--memory=256m','postgres:18.0-alpine');containers.append(db)
            for _ in range(60):
                if subprocess.run(['docker','exec',db,'pg_isready','-U','fixture'],capture_output=True).returncode==0:break
                time.sleep(.5)
            else:raise RuntimeError('Fixture database unavailable')
            url=Path(folder)/'database-url';url.write_text('postgresql+psycopg://fixture@stage71-db:5432/urumi_gateway_fixture',encoding='utf-8')
            mount=f'type=bind,source={url},target=/run/config/database-url,readonly'
            env=['-e','URUMI_DATABASE_URL_FILE=/run/config/database-url']
            common=['--network',network,'--mount',mount,*env]
            run('docker','run','--rm',*common,'urumi-gateway:stage7.1','python','-m','alembic','-c','alembic.ini','upgrade','head')
            run('docker','run','-d','--name',gateway,*common,'--read-only','--cap-drop=ALL','--security-opt=no-new-privileges:true',
                '--memory=512m','-p','127.0.0.1::8000','-e','URUMI_ENVIRONMENT=local','-e','URUMI_COOKIE_SECURE=false',
                '-e','URUMI_BROWSER_ORIGIN=http://127.0.0.1:8000','urumi-gateway:stage7.1');containers.append(gateway)
            port=json.loads(run('docker','inspect',gateway))[0]['NetworkSettings']['Ports']['8000/tcp'][0]['HostPort']
            origin='http://127.0.0.1:'+port
            wait(origin+'/api/me',401)
            assert request(origin+'/mcp')[0]==401
            security(gateway)
            print('PASS real PostgreSQL explicit migrations; gateway /api/me and /mcp authentication; no Gemini key required for startup')
            run('docker','run','-d','--name',dashboard,'--read-only','--cap-drop=ALL','--security-opt=no-new-privileges:true',
                '--tmpfs','/tmp:rw,noexec,nosuid,size=16m,uid=10001,gid=10001','--memory=128m','-p','127.0.0.1::8080',
                'urumi-dashboard:stage7.1');containers.append(dashboard)
            port=json.loads(run('docker','inspect',dashboard))[0]['NetworkSettings']['Ports']['8080/tcp'][0]['HostPort']
            origin='http://127.0.0.1:'+port;wait(origin+'/',200)
            code,html,headers=request(origin+'/');assert code==200 and 'Content-Security-Policy' in headers
            assert request(origin+'/chat')[1]==html
            assert request(origin+'/api/me')[0]==404
            for asset in re.findall(r'(?:src|href)="(/assets/[^"]+)"',html):
                status,body,_=request(origin+asset);assert status==200
                assert not re.search(r'urumi_key_[A-Za-z0-9_-]{43}|AIza[A-Za-z0-9_-]{30,}|(?:ck_|cs_)[a-f0-9]{40}',body)
            security(dashboard,False)
            print('PASS dashboard HTTP/assets/SPA fallback/security headers/asset credential scan')
            for name in (gateway,dashboard):
                run('docker','stop','-t','20',name)
                state=json.loads(run('docker','inspect',name))[0]['State']
                assert state['ExitCode']==0 and not state['OOMKilled']
                logs=run('docker','logs',name)
                assert 'Authorization:' not in logs and 'postgresql+' not in logs
            for image in ('urumi-gateway:stage7.1','urumi-dashboard:stage7.1'):
                data=json.loads(run('docker','image','inspect',image))[0]
                print(image,'bytes=',data['Size'],'id=',data['Id'])
            print('PASS clean shutdown; no real store/provider calls')
        finally:
            for name in reversed(containers):run('docker','rm','-f','-v',name,check=False)
            run('docker','network','rm',network,check=False)
if __name__=='__main__':main()
