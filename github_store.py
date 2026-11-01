"""Private GitHub snapshot storage. Credentials are server-side environment values."""
import base64,json,os,re,time,urllib.request,urllib.error
from contextlib import contextmanager
class StorageError(Exception):pass
class GitHubStore:
 def __init__(self):
  self.repo=os.environ.get('GITHUB_DATA_REPO','').strip();self.token=os.environ.get('GITHUB_DATA_TOKEN','');self.sha=None
  self.enabled=bool(self.repo or self.token)
  if self.enabled and (not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',self.repo) or not self.token):raise StorageError('Set both GITHUB_DATA_REPO and GITHUB_DATA_TOKEN.')
  self.path='quiz-records.json';self.updated=False
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
  if not repo or repo.get('private') is not True:raise StorageError('The answer repository must exist, be private and be accessible to the token.')
  record=self.request('/contents/'+self.path)
  if record is None:return None
  if record.get('encoding')!='base64' or not record.get('content'):raise StorageError('Answer snapshot is too large or unsupported; archive older quiz data.')
  self.sha=record['sha']
  try:
   value=json.loads(base64.b64decode(record['content']))
   if value.get('version')!=1 or not isinstance(value.get('classes'),list) or not isinstance(value.get('students'),list):raise ValueError()
   return value
  except (ValueError,KeyError):raise StorageError('Answer snapshot format is invalid.') from None
 def save(self,value):
  if not self.enabled:return
  content=base64.b64encode(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()).decode()
  # Contents API exposes base64 data up to 1MB. Fail visibly rather than claiming a save.
  if len(content)>950000:raise StorageError('Answer snapshot is too large; export and archive older records.')
  body={'message':'Update quiz records','content':content}
  if self.sha:body['sha']=self.sha
  result=self.request('/contents/'+self.path,'PUT',body)
  if not result or not result.get('content',{}).get('sha'):raise StorageError('GitHub did not confirm the answer save.')
  self.sha=result['content']['sha']
