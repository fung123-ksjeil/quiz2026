@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "테스트실행.py"
) else (
  python "테스트실행.py"
)
pause
