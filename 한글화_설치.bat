@echo off
chcp 65001 >nul 2>&1
title Fizgig 한글화 설치
cd /d "%~dp0.."

if exist "venv\Scripts\python.exe" goto :RUN
echo [오류] venv 가 없습니다. 먼저 install_fizgig.bat 을 실행하세요.
pause
exit /b 1

:RUN
"venv\Scripts\python.exe" "ko\tools\install.py"
if errorlevel 1 goto :FAIL
echo.
echo 설치 완료. 평소처럼 run_fizgig.bat 으로 실행하면 한글로 뜹니다.
echo (update_fizgig.bat 으로 업데이트해도 유지됩니다. venv 를 다시 만들었을 때만 이 파일을 다시 실행하세요.)
pause
exit /b 0

:FAIL
echo.
echo [실패] 위 메시지를 확인하세요.
pause
exit /b 1
