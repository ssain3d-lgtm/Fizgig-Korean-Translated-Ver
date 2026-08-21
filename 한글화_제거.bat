@echo off
chcp 65001 >nul 2>&1
title Fizgig 한글화 제거
cd /d "%~dp0.."

if exist "venv\Scripts\python.exe" goto :RUN
echo [오류] venv 가 없습니다.
pause
exit /b 1

:RUN
"venv\Scripts\python.exe" "ko\tools\install.py" --remove
echo.
echo 제거 완료. 다시 설치하려면 한글화_설치.bat 을 실행하세요.
pause
exit /b 0
