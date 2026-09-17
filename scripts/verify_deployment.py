"""Opt-in end-to-end verification of the public synthetic demonstration."""
import base64,json,sys
from http.cookiejar import CookieJar
from urllib.request import build_opener,HTTPCookieProcessor,Request
from urllib.error import HTTPError
BASE=sys.argv[1].rstrip('/') if len(sys.argv)>1 else 'https://bankclm.vercel.app'
if BASE!='https://bankclm.vercel.app': raise SystemExit('This verification script targets the authorized bankclm demonstration only.')
opener=build_opener(HTTPCookieProcessor(CookieJar()))
def call(path,method='GET',body=None,expected=200,raw=False):
    request=Request(BASE+path,data=json.dumps(body).encode() if body is not None else None,method=method,headers={'Content-Type':'application/json','Origin':BASE})
    try:
        with opener.open(request,timeout=45) as response: code=response.status;payload=response.read()
    except HTTPError as error: code=error.code;payload=error.read()
    if code!=expected: raise AssertionError(f'{path}: HTTP {code}: '+payload.decode()[:300])
    return payload if raw else json.loads(payload)

def document():
    stream=b'BT /F1 14 Tf 45 760 Td (SYNTHETIC DATA - NOT REAL CLIENT DATA) Tj 0 -30 Td (Aurelia deployment verification document) Tj ET'
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
    result=b'%PDF-1.4\n';offsets=[]
    for i,obj in enumerate(objects,1): offsets.append(len(result));result+=f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n'
    start=len(result);result+=b'xref\n0 6\n0000000000 65535 f \n'+b''.join(f'{n:010d} 00000 n \n'.encode() for n in offsets)
    return result+f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF'.encode()

health=call('/health');assert health['storage']=='postgresql'
call('/api/state')
c=call('/api/cases','POST',dict(name='Aurelia Demo Verification',email='synthetic@example.com',type='Individual',risk='Low',residency='Singapore',aum=0,owner='Demo verification'),201)
cid=c['id'];path='/api/cases/'+cid
call(path+'/transition','POST',{'action':'Submit for review'},400)
call('/api/session','POST',{'role':'Client','clientId':cid})
assert len(call('/api/state')['cases'])==1
call(path,'PATCH',dict(taxResidency='Singapore',sourceOfWealth='Synthetic deployment verification only',consent=True))
content=document()
for category in call('/api/state')['cases'][0]['requiredDocuments']:
    call(path+'/documents','POST',dict(name='synthetic-demo.pdf',type=category,content=base64.b64encode(content).decode()),201)
call('/api/session','POST',{'role':'Relationship manager'})
call(path+'/transition','POST',{'action':'Submit for review'})
call(path+'/transition','POST',{'action':'Request approval'},400)
call('/api/session','POST',{'role':'Compliance'})
c=next(x for x in call('/api/state')['cases'] if x['id']==cid)
for d in c['documents']: call(path+'/documents/'+d['id']+'/review','POST',dict(status='Verified',note='Synthetic deployment verification'))
for key in ['identity','screening','wealth','tax']: call(path+'/kyc','PUT',dict(check=key,checked=True,note='Synthetic manual test attestation; no external screening'))
call('/api/session','POST',{'role':'Relationship manager'})
call(path+'/transition','POST',{'action':'Request approval'})
call('/api/session','POST',{'role':'Compliance'})
call(path+'/transition','POST',{'action':'Approve & activate'})
assert call(path+'/documents/'+c['documents'][0]['id'],raw=True)==content
call(path+'/transition','POST',{'action':'Offboard client','note':'Completed synthetic deployment verification; archived for demo evidence'})
# A fresh browser session must see the persisted result.
opener=build_opener(HTTPCookieProcessor(CookieJar()))
assert next(x for x in call('/api/state')['cases'] if x['id']==cid)['stageKind']=='closed'
print(json.dumps({'passed':True,'case':cid,'verified':['client isolation','upload','document review','KYC','approval gates','independent activation','file download','closure','fresh-session persistence']}))
