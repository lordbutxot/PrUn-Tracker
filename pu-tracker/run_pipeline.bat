@echo off
setlocal enabledelayedexpansion

REM --- ENVIRONMENT SETUP ---
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
set PRUN_SPREADSHEET_ID=1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI

REM --- LOGGING SETUP ---
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "TIMESTAMP=%YYYY%%MM%%DD%_%HH%%Min%%Sec%"
set "LOGFILE=logs\pipeline_%TIMESTAMP%.log"

if not exist "logs" mkdir logs
if not exist "cache" mkdir cache

echo ========================================
echo    PrUn-Tracker Unified Pipeline
echo ========================================
echo Started at %date% %time%
echo Logging to %LOGFILE%
echo.

REM --- RUN THE MAIN PIPELINE ---
python historical_data\main.py | python dual_logger.py "%LOGFILE%"

REM --- COMPLETION STATUS ---
set PIPELINE_RESULT=%errorlevel%
echo.
if %PIPELINE_RESULT% neq 0 (
    echo [ERROR] Pipeline failed (exit code %PIPELINE_RESULT%)
    echo Check %LOGFILE% for details
    pause
    exit /b %PIPELINE_RESULT%
) else (
    echo Pipeline completed successfully!
    echo Log saved to: %LOGFILE%
    pause
    exit /b 0
)
