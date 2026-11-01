"""Password persistence, session revocation, and remote-save rollback checks."""
import unittest,secrets,json
from pathlib import Path
import test_server as base
import test_github_store as remote
class PasswordMixin:
 def test_password_change(self):
  admin=self.client();other=self.client();anonymous=self.client();new=secrets.token_urlsafe(24)
  for client in [admin,other]:self.assertEqual(self.req(client,'/api/admin/login',{'password':self.password})[0],200)
  self.assertEqual(self.req(admin,'/api/admin/classes',{'name':'기록 보존 반','code':'6543'})[0],200)
  classroom=json.loads(self.req(admin,'/api/admin/status')[1])['classes'][0]
  self.assertEqual(self.req(admin,'/api/admin/toggle',{'id':classroom['id'],'opened':True})[0],200)
  student=self.client();self.assertEqual(self.req(student,'/api/join',{'code':'6543','studentId':'1001','name':'기록 보존'})[0],200)
  self.assertEqual(self.req(student,'/api/answers',{'answers':{'1':2}})[0],200)
  payload={'currentPassword':self.password,'newPassword':new,'confirmPassword':new}
  self.assertEqual(self.req(anonymous,'/api/admin/password',payload)[0],401)
  self.assertEqual(self.req(admin,'/api/admin/password',{**payload,'currentPassword':'wrong'})[0],400)
  self.assertEqual(self.req(admin,'/api/admin/password',{**payload,'confirmPassword':'different'})[0],400)
  self.assertEqual(self.req(admin,'/api/admin/password',{**payload,'newPassword':'123','confirmPassword':'123'})[0],400)
  remote_file=Path(self.tmp.name)/'remote.json'
  if remote_file.exists():
   before=remote_file.read_bytes();marker=remote_file.with_suffix('.fail');marker.touch()
   try:
    self.assertEqual(self.req(admin,'/api/admin/password',payload)[0],503)
    self.assertEqual(remote_file.read_bytes(),before)
    self.assertEqual(self.req(other,'/api/admin/status')[0],200)
    self.assertEqual(self.req(anonymous,'/api/admin/login',{'password':new})[0],401)
    self.assertEqual(self.req(anonymous,'/api/admin/login',{'password':self.password})[0],200)
   finally:marker.unlink()
  self.assertEqual(self.req(admin,'/api/admin/password',payload)[0],200)
  self.assertEqual(self.req(admin,'/api/admin/status')[0],401)
  self.assertEqual(self.req(other,'/api/admin/status')[0],401)
  self.assertEqual(json.loads(self.req(student,'/api/exam')[1])['answers'],{'1':2})
  self.assertEqual(self.req(admin,'/api/admin/login',{'password':self.password})[0],401)
  self.assertEqual(self.req(admin,'/api/admin/login',{'password':new})[0],200)
  public_admin=self.req(admin,'/api/admin/content')[1]+self.req(admin,'/api/admin/status')[1]
  self.assertNotIn(new.encode(),public_admin);self.assertNotIn(b'admin_password',public_admin)
  self.proc.terminate();self.proc.wait();type(self).start()
  self.assertEqual(self.req(admin,'/api/admin/login',{'password':self.password})[0],401)
  self.assertEqual(self.req(admin,'/api/admin/login',{'password':new})[0],200)
  restored=json.loads(self.req(admin,'/api/admin/status')[1]);self.assertEqual(restored['students'][0]['answers'],{'1':2});self.assertEqual(restored['classes'][0]['code'],'6543')
  newer=secrets.token_urlsafe(24)
  self.assertEqual(self.req(admin,'/api/admin/password',{'currentPassword':new,'newPassword':newer,'confirmPassword':newer})[0],200)
  self.assertEqual(self.req(admin,'/api/admin/login',{'password':newer})[0],200)
  for _ in range(5):self.assertEqual(self.req(admin,'/api/admin/password',{'currentPassword':'wrong','newPassword':new,'confirmPassword':new})[0],400)
  self.assertEqual(self.req(admin,'/api/admin/password',{'currentPassword':'wrong','newPassword':new,'confirmPassword':new})[0],429)
class LocalPasswordTests(PasswordMixin,base.ExamTests):
 test_lifecycle=None
class GitHubPasswordTests(PasswordMixin,remote.GitHubPersistenceTests):
 test_lifecycle=None
 test_remote_write_failure=None
if __name__=='__main__':unittest.main(verbosity=2)
