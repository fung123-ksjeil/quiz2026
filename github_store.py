"""Encrypted snapshots on a separate GitHub data branch; no client-side credentials."""
import base64,hashlib,json,os,re,time,zlib,urllib.request,urllib.error
from contextlib import contextmanager
class StorageError(Exception):pass
class GitHubStore:
 def __init__(self):
  self.repo=os.environ.get('GITHUB_DATA_REPO','').strip();self.token=os.environ.get('GITHUB_DATA_TOKEN','');self.sha=None
  self.enabled=bool(self.repo or self.token)
  if self.enabled and (not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',self.repo) or not self.token):raise StorageError('Set both GITHUB_DATA_REPO and GITHUB_DATA_TOKEN.')
  self.path='quiz-records.enc';self.branch='quiz-data';self.cipher=None
  if self.enabled:
   secret=os.environ.get('QUIZ_DATA_KEY','')
   if len(secret)<32:raise StorageError('Set QUIZ_DATA_KEY to a stable random secret of at least 32 characters. Do not use the admin password.')
   from cryptography.fernet import Fernet
   self.cipher=Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))
 def request(self,path,method='GET',body=None):
  request=urllib.request.Request('https://api.github.com/repos/'+self.repo+path,method=method,data=json.dumps(body).encode() if body is not None else None,headers={'Authorization':'Bearer '+self.token,'Accept':'application/vnd.github+json','Content-Type':'application/json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'quiz2026-storage'})
  try:
   with urllib.request.urlopen(request,timeout=15) as response:return json.load(response)
  except urllib.error.HTTPError as error:
   if error.code==404:return None
   raise StorageError('GitHub storage request failed (HTTP '+str(error.code)+').') from None
  except (OSError,ValueError):raise StorageError('GitHub storage is unavailable.') from None
 def load(self):
  if not self.enabled:return None
  repo=self.request('')
  if not repo:raise StorageError('The answer repository must exist and be accessible to the token.')
  ref=self.request('/git/ref/heads/'+self.branch)
  if ref is None:
   default=repo.get('default_branch','main')
   source=self.request('/git/ref/heads/'+default)
   if not source or not source.get('object',{}).get('sha'):raise StorageError('The repository must contain an initial commit.')
   created=self.request('/git/refs','POST',{'ref':'refs/heads/'+self.branch,'sha':source['object']['sha']})
   if not created:raise StorageError('GitHub did not confirm creation of the data branch.')
  record=self.request('/contents/'+self.path+'?ref='+self.branch)
  if record is None:return None
  if record.get('encoding')!='base64' or not record.get('content'):raise StorageError('Answer snapshot is too large or unsupported; archive older quiz data.')
  self.sha=record['sha']
  try:
   value=self.decode_snapshot(base64.b64decode(record['content']))
   if value.get('version')!=1 or not isinstance(value.get('classes'),list) or not isinstance(value.get('students'),list):raise ValueError()
   return value
  except Exception:raise StorageError('Unable to decrypt the answer snapshot. Verify the original QUIZ_DATA_KEY; do not replace it.') from None
 def encode_snapshot(self,value):
  plain=json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()
  if len(plain)>32*1024*1024:raise StorageError('The quiz archive exceeds the supported size.')
  return self.cipher.encrypt(b'QZ2\0'+zlib.compress(plain,9))
 def decode_snapshot(self,encrypted):
  plain=self.cipher.decrypt(encrypted)
  if plain.startswith(b'QZ2\0'):
   decoder=zlib.decompressobj();plain=decoder.decompress(plain[4:],32*1024*1024+1)
   if len(plain)>32*1024*1024 or decoder.unconsumed_tail or not decoder.eof:raise StorageError('The quiz archive is too large or corrupt.')
  return json.loads(plain)
 def save(self,value):
  if not self.enabled:return
  encrypted=self.encode_snapshot(value)
  content=base64.b64encode(encrypted).decode()
  # Contents API exposes base64 data up to 1MB. Fail visibly rather than claiming a save.
  if len(content)>950000:raise StorageError('Answer snapshot is too large; export and archive older records.')
  body={'message':'Update encrypted quiz records','content':content,'branch':self.branch}
  if self.sha:body['sha']=self.sha
  result=self.request('/contents/'+self.path,'PUT',body)
  if not result or not result.get('content',{}).get('sha'):raise StorageError('GitHub did not confirm the answer save.')
  self.sha=result['content']['sha']
