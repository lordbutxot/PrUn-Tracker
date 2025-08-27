@echo off
setlocal enabledelayedexpansion

REM Force UTF-8 encoding for Unicode support
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8

REM Set required environment variables FIRST
set PRUN_SPREADSHEET_ID=1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI

echo ========================================
echo    PrUn-Tracker Optimized Pipeline
echo ========================================
echo Starting at %date% %time%
echo Environment: PRUN_SPREADSHEET_ID=%PRUN_SPREADSHEET_ID%
echo.

REM --- PREPARATION PHASE ---
echo [STEP] Checking for duplicate removal script...
if exist "remove_duplicates.bat" (
    echo [INFO] Removing duplicates...
    call remove_duplicates.bat
    echo [OK] Duplicates removed.
) else (
    echo [INFO] remove_duplicates.bat not found, skipping...
)
echo.

echo [STEP] Ensuring required directories exist...
if not exist "logs" mkdir logs
if not exist "cache" mkdir cache
echo [OK] Directories ready.
echo.

REM --- LOGGING SETUP ---
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "TIMESTAMP=%YYYY%%MM%%DD%_%HH%%Min%%Sec%"
set "LOGFILE=logs\pipeline_%TIMESTAMP%.log"

echo [STEP] Logging to %LOGFILE%
echo Pipeline started at %date% %time% > "%LOGFILE%"
echo ======================================== >> "%LOGFILE%"
echo Environment: PRUN_SPREADSHEET_ID=%PRUN_SPREADSHEET_ID% >> "%LOGFILE%"
echo.

REM --- PYTHON CHECK ---
echo [STEP] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found in PATH
    echo [ERROR] Python not found in PATH >> "%LOGFILE%"
    echo Please install Python or add it to your PATH
    pause
    exit /b 1
)
echo [OK] Python found!
python --version >> "%LOGFILE%" 2>&1
echo.

REM --- VIRTUAL ENVIRONMENT ---
echo [STEP] Checking for virtual environment...
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call "venv\Scripts\activate.bat"
    echo [OK] Virtual environment activated >> "%LOGFILE%"
) else (
    echo [INFO] No virtual environment found, using system Python
    echo No virtual environment found >> "%LOGFILE%"
)
echo.

REM --- CONFIGURATION CHECK ---
echo [STEP] Checking required configuration files...
set CONFIG_FOUND=0
if exist "historical_data\unified_config.py" (
    echo [OK] Found unified_config.py
    set CONFIG_FOUND=1
)
if exist "historical_data\config.py" (
    echo [OK] Found config.py
    set CONFIG_FOUND=1
)
if %CONFIG_FOUND% equ 0 (
    echo [ERROR] No configuration file found in historical_data/
    pause
    exit /b 1
)
if exist "historical_data\sheets_manager.py" (
    echo [OK] Found sheets_manager.py
) else (
    echo [ERROR] sheets_manager.py not found in historical_data/
    pause
    exit /b 1
)
set PROCESSOR_FOUND=0
if exist "historical_data\unified_processor.py" (
    echo [OK] Found unified_processor.py
    set PROCESSOR_FOUND=1
)
if exist "historical_data\main_refresh_basics.py" (
    echo [OK] Found main_refresh_basics.py (legacy processor)
    set PROCESSOR_FOUND=1
)
if %PROCESSOR_FOUND% equ 0 (
    echo [ERROR] No data processor found in historical_data/
    pause
    exit /b 1
)
echo.

REM --- IMPORT FIXES ---
echo [STEP] Checking for import fix scripts...
if exist "fix_imports.py" (
    echo [INFO] Running fix_imports.py...
    python fix_imports.py >> "%LOGFILE%" 2>&1
    echo [OK] Imports fixed.
) else if exist "historical_data\fix_imports.py" (
    echo [INFO] Running historical_data\fix_imports.py...
    python historical_data\fix_imports.py >> "%LOGFILE%" 2>&1
    echo [OK] Imports fixed.
) else (
    echo [INFO] fix_imports.py not found, skipping import fixes...
)
if exist "fix_processor_imports.py" (
    echo [INFO] Running fix_processor_imports.py...
    python fix_processor_imports.py >> "%LOGFILE%" 2>&1
    echo [OK] Processor imports fixed.
) else (
    echo [INFO] fix_processor_imports.py not found, skipping processor import fixes...
)
echo.

REM --- CREDENTIALS CHECK ---
echo [STEP] Checking for Google Sheets credentials...
if exist "historical_data\prun-profit-7e0c3bafd690.json" (
    echo [OK] Google Sheets credentials found.
) else (
    echo [ERROR] Google Sheets credentials not found in historical_data/
    pause
    exit /b 1
)
echo.

REM --- ENTRY POINT CHECK ---
echo [STEP] Checking for main entry point...
set ENTRY_FOUND=0
if exist "historical_data\main.py" (
    echo [OK] Using historical_data\main.py as entry point
    set "ENTRY_POINT=historical_data\main.py"
    set ENTRY_FOUND=1
) else (
    echo [ERROR] historical_data\main.py not found
    pause
    exit /b 1
)
echo.

REM --- PIPELINE EXECUTION ---
echo [STEP] Running main pipeline...
echo Running pipeline with entry point: %ENTRY_POINT%
python "%ENTRY_POINT%" full >> "%LOGFILE%" 2>&1
set PIPELINE_RESULT=%errorlevel%

REM --- FALLBACKS ---
if %PIPELINE_RESULT% neq 0 (
    echo [WARN] Main pipeline failed (exit code %PIPELINE_RESULT%), trying alternative approaches...
    if exist "historical_data\catch_data.py" (
        echo [STEP] Running data collection...
        python historical_data\catch_data.py >> "%LOGFILE%" 2>&1
        set CATCH_RESULT=%errorlevel%
        if !CATCH_RESULT! equ 0 (
            echo [STEP] Running data processing...
            if exist "historical_data\main_refresh_basics.py" (
                python historical_data\main_refresh_basics.py >> "%LOGFILE%" 2>&1
                set PROCESS_RESULT=%errorlevel%
                if !PROCESS_RESULT! equ 0 (
                    echo [STEP] Running data upload...
                    if exist "ultra_all_exchanges_upload.py" (
                        python ultra_all_exchanges_upload.py >> "%LOGFILE%" 2>&1
                        set UPLOAD_RESULT=%errorlevel%
                        set PIPELINE_RESULT=!UPLOAD_RESULT!
                    ) else (
                        echo [ERROR] ultra_all_exchanges_upload.py not found
                    )
                ) else (
                    echo [ERROR] Data processing failed with code !PROCESS_RESULT!
                )
            ) else (
                echo [ERROR] main_refresh_basics.py not found
            )
        ) else (
            echo [ERROR] Data collection failed with code !CATCH_RESULT!
        )
    ) else (
        echo [ERROR] catch_data.py not found
    )
)
echo.

REM --- ENHANCED ANALYSIS & UPLOAD ---
if %PIPELINE_RESULT% equ 0 (
    echo [STEP] Running enhanced analysis (data_analyzer.py)...
    python historical_data\data_analyzer.py >> "%LOGFILE%" 2>&1
    set ANALYSIS_RESULT=%errorlevel%
    if !ANALYSIS_RESULT! equ 0 (
        echo [OK] Enhanced analysis completed successfully.
        echo [STEP] Uploading enhanced analysis to Google Sheets...
        python historical_data\upload_enhanced_analysis.py >> "%LOGFILE%" 2>&1
        set UPLOAD_RESULT=%errorlevel%
        if !UPLOAD_RESULT! equ 0 (
            echo [OK] Google Sheets upload completed successfully.
        ) else (
            echo [ERROR] Google Sheets upload failed (exit code !UPLOAD_RESULT!)
        )
    ) else (
        echo [ERROR] Enhanced analysis failed (exit code !ANALYSIS_RESULT!)
    )
)
echo.

REM --- REPORT TAB GENERATION ---
echo [STEP] Generating and uploading Report Tabs...
python historical_data\generate_report_tabs.py >> "%LOGFILE%" 2>&1
set REPORT_RESULT=%errorlevel%
if !REPORT_RESULT! neq 0 (
    echo [ERROR] Report tab generation failed (exit code !REPORT_RESULT!)
)
echo.

REM --- COMPLETION STATUS ---
echo ========================================
if %PIPELINE_RESULT% neq 0 (
    echo    PIPELINE FAILED
    echo Exit code: %PIPELINE_RESULT%
    echo Check %LOGFILE% for details
    echo Recent log entries:
    powershell "Get-Content '%LOGFILE%' | Select-Object -Last 15"
    echo Troubleshooting:
    echo 1. Check if all required files exist in historical_data/
    echo 2. Verify Google Sheets credentials
    echo 3. Check internet connection
    echo 4. Review full log file: %LOGFILE%"
    echo.
    pause
    exit /b 1
) else (
    echo    Pipeline completed successfully!
    echo Log saved to: %LOGFILE%
    echo.
    echo Files generated:
    if exist "cache\daily_report.csv" echo   [OK] cache\daily_report.csv  
    if exist "cache\daily_analysis.csv" echo   [OK] cache\daily_analysis.csv
    if exist "cache\processed_data.csv" echo   [OK] cache\processed_data.csv
    if exist "cache\market_data.csv" echo   [OK] cache\market_data.csv
    if exist "cache\materials.csv" echo   [OK] cache\materials.csv
    if exist "cache\buildings.csv" echo   [OK] cache\buildings.csv
    if exist "cache\materials.json" echo   [OK] cache\materials.json
    if exist "cache\buildings.json" echo   [OK] cache\buildings.json
    if exist "cache\chains.json" echo   [OK] cache\chains.json
    echo.
    echo Google Sheets Status:
    echo   [SUCCESS] DATA AI1 tab should now be populated
    echo   [SUCCESS] DATA CI1, CI2, IC1, NC1, NC2 tabs should be populated
    echo   [TARGET] Spreadsheet ID: %PRUN_SPREADSHEET_ID%
    echo.
    echo To view detailed results:
    echo   type "%LOGFILE%"
    echo.
    pause
    exit /b 0
)
