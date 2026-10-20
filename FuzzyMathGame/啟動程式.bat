@echo off
chcp 65001 >nul

cd /d "%~dp0backend"

REM 設定 MySQL 資料庫密碼
set "FUZZY_DB_PASSWORD=arod0316"

REM 開啟遊戲網頁
start "" http://127.0.0.1:5000/

set "FUZZY_DATA_MODE=mysql_dev"

REM 啟動 Flask 後端
python app.py

pause
