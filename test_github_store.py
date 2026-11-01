"""Simulated GitHub API only. Does not send credentials or student records externally."""
import unittest,os,json,base64,hashlib,subprocess,time,urllib.request
from unittest.mock import patch
from pathlib import Path
from github_store import GitHubStore, StorageError
from test_server import ExamTests

def fake_request(self,path,method='GET',body=None):
 file=Path(os.environ['FAKE_GITHUB_FILE'])
 if path=='':return {'private':False,'default_branch':'main'}
 if path.startswith('/git/ref/'):return {'object':{'sha':'main-commit'}}
 record=json.loads(file.read_text()) if file.exists() else None
 if method=='GET':return record
 if record and body.get('sha')!=record['sha']:raise StorageError('Conflict')
 if file.with_suffix('.fail').exists():raise StorageError('simulated outage')
 content=body['content'];sha=hashlib.sha256(content.encode()).hexdigest()
 file.write_text(json.dumps({'sha':sha,'encoding':'base64','content':content}))
 return {'content':{'sha':sha}}

class GitHubPersistenceTests(ExamTests):
 @classmethod
 def start(cls):
  # Discard all local SQLite data, as happens on a free-server redeployment.
  db=Path(cls.tmp.name)/'exam.sqlite3'
  if db.exists():db.unlink()
  env={**os.environ,'ADMIN_PASSWORD':cls.password,'QUIZ_DATA_DIR':cls.tmp.name,'PORT':str(cls.port),'QUIZ_DATA_KEY':cls.password,'GITHUB_DATA_REPO':'test/public-data','GITHUB_DATA_TOKEN':'test-only-not-a-credential','FAKE_GITHUB_FILE':str(Path(cls.tmp.name)/'remote.json')}
  code="import github_store; from test_github_store import fake_request; github_store.GitHubStore.request=fake_request; import server; server.ThreadingHTTPServer(('127.0.0.1',int(__import__('os').environ['PORT'])),server.Handler).serve_forever()"
  cls.proc=subprocess.Popen(['python3','-c',code],cwd=Path(__file__).parent,env=env,stdout=subprocess.DEVNULL)
  for _ in range(100):
   try:urllib.request.build_opener(urllib.request.ProxyHandler({})).open(cls.base,timeout=.2);return
   except OSError:time.sleep(.05)
  raise RuntimeError('Mock-backed server failed to start')

 def test_remote_write_failure(self):
  admin=self.client();self.assertEqual(self.req(admin,'/api/admin/login',{'password':self.password})[0],200)
  classes=json.loads(self.req(admin,'/api/admin/status')[1])['classes']
  target=Path(self.tmp.name)/'remote.json';before=target.read_text();marker=target.with_suffix('.fail');marker.touch()
  try:
   self.assertEqual(self.req(admin,'/api/admin/toggle',{'id':classes[0]['id'],'opened':True})[0],503)
   self.assertEqual(target.read_text(),before)
   self.assertTrue(json.loads(self.req(admin,'/api/admin/status')[1])['storage']['pending'])
  finally:marker.unlink()
  self.assertEqual(self.req(admin,'/api/admin/toggle',{'id':classes[0]['id'],'opened':True})[0],200)
  self.assertNotEqual(target.read_text(),before)

class StoreTests(unittest.TestCase):
 def store(self):
  with patch.dict(os.environ,{'GITHUB_DATA_REPO':'test/public','GITHUB_DATA_TOKEN':'test-only','QUIZ_DATA_KEY':'test-only-storage-key-at-least-32-characters'}):return GitHubStore()
 def test_missing_key_rejected(self):
  with patch.dict(os.environ,{'GITHUB_DATA_REPO':'test/public','GITHUB_DATA_TOKEN':'test-only','QUIZ_DATA_KEY':''}):
   with self.assertRaises(StorageError):GitHubStore()
 def test_public_repo_encrypted_roundtrip(self):
  s=self.store();payload={'version':1,'classes':[],'students':[{'name':'학생이름','student_id':'10301','answers':'답안'}]}
  with patch.object(s,'request',return_value={'content':{'sha':'new'}}) as call:
   s.save(payload);body=call.call_args.args[2];self.assertEqual(body['branch'],'quiz-data')
   encrypted=base64.b64decode(body['content']);self.assertNotIn('학생이름'.encode(),encrypted);self.assertNotIn(b'10301',encrypted)
   self.assertEqual(json.loads(s.cipher.decrypt(encrypted)),payload)
  record={'sha':'new','encoding':'base64','content':body['content']}
  responses=[{'private':False,'default_branch':'main'},{'object':{'sha':'branch'}},record]
  with patch.object(s,'request',side_effect=responses) as call:
   self.assertEqual(s.load(),payload);self.assertIn('?ref=quiz-data',call.call_args.args[0])
  with patch.object(s,'request',side_effect=StorageError('network')):
   with self.assertRaises(StorageError):s.save(payload)
   self.assertEqual(s.sha,'new')
  wrong=self.store()
  from cryptography.fernet import Fernet
  wrong.cipher=Fernet(Fernet.generate_key())
  with patch.object(wrong,'request',side_effect=responses):
   with self.assertRaises(StorageError):wrong.load()
 def test_create_separate_branch(self):
  s=self.store()
  with patch.object(s,'request',side_effect=[{'private':False,'default_branch':'main'},None,{'object':{'sha':'main-sha'}},{'ref':'refs/heads/quiz-data'},None]) as call:
   self.assertIsNone(s.load());creation=call.call_args_list[3];self.assertEqual(creation.args[2],{'ref':'refs/heads/quiz-data','sha':'main-sha'})
 def test_size_limit(self):
  with self.assertRaises(StorageError):self.store().save({'large':'x'*1000000})
if __name__=='__main__':unittest.main(verbosity=2)
