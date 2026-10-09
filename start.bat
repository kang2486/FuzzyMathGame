
@echo off
chcp 65001 >nul
title FuzzyMathGame
cd /d "%~dp0backend"

echo 正在啟動 FuzzyMathGame...
echo 請確認 MySQL 服務已啟動。
echo.

start "" http://127.0.0.1:5000/
python app.py

pause
