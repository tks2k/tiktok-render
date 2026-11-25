import numpy as np, subprocess, requests, json, time, hashlib, tarfile
def dec(f): return np.frombuffer(subprocess.run([FF,'-v','error','-i',f,'-f','s16le','-ac','1','-ar','44100','-'],capture_output=True).stdout,dtype=np.int16).astype(np.float32)
def enc(y,out): subprocess.run([FF,'-y','-v','error','-f','s16le','-ar','44100','-ac','1','-i','-','-b:a','192k',out],input=np.clip(y,-32767,32767).astype(np.int16).tobytes())
def squeeze(src,out='vo.mp3',keep=0.12):
    a=dec(src); fl=441; n=len(a)//fl; db=20*np.log10(np.sqrt((a[:n*fl].reshape(n,fl)**2).mean(1)+1e-9)); loud=db>db.max()-38
    segs=[]; i=0; K=int(keep*100)
    while i<n:
        j=i
        while j<n and loud[j]==loud[i]: j+=1
        if not loud[i] and (j-i)>K: h=K//2; segs.append((i*fl,(i+h)*fl)); segs.append(((j-(K-h))*fl,j*fl))
        else: segs.append((i*fl,j*fl))
        i=j
    y=np.concatenate([a[s:e] for s,e in segs]); enc(y,out); return len(y)/44100
def loopbed(src,out,secs,X=0.25):
    w=dec(src); X=int(X*44100); parts=[w[:-X]]
    while sum(len(p) for p in parts)<secs*44100:
        f=np.linspace(0,1,X); parts.append(w[-X:]*(1-f)+w[:X]*f); parts.append(w[X:-X])
    enc(np.concatenate(parts),out)
FOLDER='1K21t1UdTvCFzIrO7n7CXcNVdkx0326GO'
def drive2(d,files):
    for f,mt in files:
        with contextlib.redirect_stdout(io.StringIO()):
            u,e=upload_local_file(d+'/'+f); s3=u.get('s3key') or u.get('data',{}).get('s3key')
            r,e=run_composio_tool('GOOGLEDRIVE_RESUMABLE_UPLOAD',{'file_to_upload':{'name':f,'mimetype':mt,'s3key':s3},'folder_to_upload_to':FOLDER,'metadata':{'name':f}},account='tiktok')
        print(f, e or 'ok')
def asrfile(p):
    subprocess.run([FF,'-y','-v','error','-i',p,'-vn','-ac','1','-ar','16000','/tmp/chk.wav']); return asr('/tmp/chk.wav')
