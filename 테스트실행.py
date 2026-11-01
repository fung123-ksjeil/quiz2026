"""Local test launcher. Password is kept only in this process."""
import getpass, os, socket, webbrowser
from pathlib import Path
os.chdir(Path(__file__).resolve().parent)
print('6단원 온라인 시험지 - 내 컴퓨터 테스트')
print('Python 3.10 이상이 필요합니다. 종료하려면 이 창에서 Ctrl+C를 누르세요.')
if not os.environ.get('ADMIN_PASSWORD') and not Path('admin_auth.json').is_file():
 while True:
  password=getpass.getpass('사용할 관리자 비밀번호를 입력하세요 (6자 이상): ')
  if len(password)>=6:break
  print('6자 이상 입력해 주세요.')
 os.environ['ADMIN_PASSWORD']=password
 del password
else:print('관리자 비밀번호 설정을 불러왔습니다.')
import server
http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
port=http.server_address[1]
base=f'http://127.0.0.1:{port}'
print('\n관리자 화면: '+base+'/admin')
print('학생 시험 입장: '+base+'/')
print('연습문제 모드: '+base+'/practice')
print('\n관리자 창에서 반 생성 → 공개 → 응시 코드 복사 후, 학생 화면에 입력하세요.')
print('같은 컴퓨터의 다른 브라우저 또는 시크릿 창으로 학생 화면을 열면 구분해서 테스트할 수 있습니다.')
print('이 주소는 현재 컴퓨터에서만 접속됩니다. 창을 닫으면 서버가 종료됩니다.\n')
webbrowser.open(base+'/admin')
try:http.serve_forever()
except KeyboardInterrupt:print('\n테스트 서버를 종료합니다.')
finally:http.server_close()
