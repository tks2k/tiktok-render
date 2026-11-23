import subprocess, sys, base64, json, os, hashlib, io, contextlib, time, shutil, tarfile
import requests as rq
r=subprocess.run([sys.executable,'-m','pip','install','-q','faster-whisper','imageio-ffmpeg'],capture_output=True,text=True)
import imageio_ffmpeg, numpy as np
FF=imageio_ffmpeg.get_ffmpeg_exe()
REPO='/repos/tks2k/tiktok-render'
def gh(method, ep, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return proxy_execute(method, ep, 'github', **kw)
def put(path, data, msg):
    if isinstance(data,str): data=data.encode()
    g,e=gh('GET',f'{REPO}/contents/{path}')
    sha=g.get('sha') if isinstance(g,dict) else None
    body={'message':msg,'content':base64.b64encode(data).decode()}
    if sha: body['sha']=sha
    r,e=gh('PUT',f'{REPO}/contents/{path}',body=body)
    return e or 'ok'
def load16(p):
    raw=subprocess.run([FF,'-v','error','-i',p,'-f','s16le','-ac','1','-ar','16000','-'],capture_output=True).stdout
    return np.frombuffer(raw,np.int16).astype(np.float32)/32768
from faster_whisper import WhisperModel
M=WhisperModel('tiny',device='cpu',compute_type='int8',cpu_threads=1)
def asr(p):
    segs,_=M.transcribe(load16(p),language='de',word_timestamps=True)
    return [(w.word.strip(),round(float(w.start),2)) for s in segs for w in s.words]
def waitprev(limit=170):
    t0=time.time()
    while time.time()-t0<limit:
        r,e=gh('GET',f'{REPO}/actions/runs',query_params={'per_page':'1'}); x=r['workflow_runs'][0]
        if x['status']=='completed': break
        time.sleep(10)
    print(x['name'],x['status'],x['conclusion'],x['created_at'],x['updated_at'])
def undraft():
    for k in range(6):
        rr,e=gh('GET',f'{REPO}/releases',query_params={'per_page':'3'})
        for rel in [r for r in rr if r['draft']]:
            gh('PATCH',f"{REPO}/releases/{rel['id']}",body={'draft':False,'tag_name':rel['tag_name']}); print('undrafted',rel['tag_name']); return
        time.sleep(8)
g,e=gh('GET',f'{REPO}/contents/videos/airbag/video.html')
open('/home/user/airbag.html','wb').write(rq.get(g['download_url']).content)
def build(d):
    os.chdir(d); exec(open('build.py').read().replace('/home/claude/airbag.html','/home/user/airbag.html'), {})
    return open('video.html','rb').read()
def apply(b64, times=None, msg='edit', d=None, vid=None):
    os.chdir(d); exec(base64.b64decode(b64).decode(), {})
    h=build(d); print(hashlib.md5(h).hexdigest()); print(put(f'videos/{vid}/video.html',h,msg))
    if times: r,e=gh('POST',f'{REPO}/actions/workflows/preview.yml/dispatches',body={"ref":"main","inputs":{"video":vid,"times":times}}); print(e)
def mix(END, CUES, tempo=1.15):
    subprocess.run([FF,'-y','-v','error','-i','vo.mp3','-af',f'atempo={tempo},apad,atrim=0:{END}','-ar','44100','-ac','2','-c:a','aac','-b:a','192k','sprecher.m4a'])
    ins=[];fl=[]
    for i,(n,t,db,dd) in enumerate(CUES):
        ins+=(['-stream_loop','-1'] if n=='atmo' else [])+['-i',n+'.mp3']
        fl.append(f'[{i}:a]aresample=44100,aformat=channel_layouts=stereo,atrim=0:{dd},afade=t=in:d=0.05,afade=t=out:st={max(0,dd-0.3)}:d=0.3,volume={db-6}dB,adelay={int(t*1000)}|{int(t*1000)}[s{i}]')
    n=len(CUES); ins+=['-i','sprecher.m4a']
    fl.append(''.join(f'[s{i}]' for i in range(n))+f'amix=inputs={n}:normalize=0,apad,atrim=0:{END}[mx]'); fl.append(f'[{n}:a]aformat=channel_layouts=stereo[key]'); fl.append('[mx][key]sidechaincompress=threshold=0.03:ratio=4[out]')
    r=subprocess.run([FF,'-y','-v','error']+ins+['-filter_complex',';'.join(fl),'-map','[out]','-t',str(END),'-c:a','aac','-b:a','192k','effekte.m4a'],capture_output=True,text=True); print(r.stderr[-300:])
def drive(files):
    FOLDER='1K21t1UdTvCFzIrO7n7CXcNVdkx0326GO'
    for f,mt in files:
        with contextlib.redirect_stdout(io.StringIO()):
            u,e=upload_local_file(f); s3=u.get('s3key') or u.get('data',{}).get('s3key')
            r,e=run_composio_tool('GOOGLEDRIVE_RESUMABLE_UPLOAD',{'file_to_upload':{'name':f,'mimetype':mt,'s3key':s3},'folder_to_upload_to':FOLDER,'metadata':{'name':f}},account='tiktok')
        print(f, e or 'ok')
print('init ok')
