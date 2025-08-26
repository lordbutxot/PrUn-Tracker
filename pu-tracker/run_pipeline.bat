@echo off
echo ========================================
echo    PrUn-Tracker 3-Step Pipeline
echo ========================================
echo.

echo [STEP 1/3] Running Data Collection
echo ----------------------------------------
python main.py catch
if %errorlevel% neq 0 (
    echo ERROR in data collection - Stopping pipeline
    pause
    exit /b 1
)
echo.

echo [STEP 2/3] Running Data Processing  
echo ----------------------------------------
python main.py process
if %errorlevel% neq 0 (
    echo ERROR in data processing - Stopping pipeline
    pause
    exit /b 1
)
echo.

echo [STEP 3/3] Running Data Upload/Validation
echo ----------------------------------------
python main.py upload
if %errorlevel% neq 0 (
    echo ERROR in data upload - Stopping pipeline
    pause
    exit /b 1
)
echo.

echo ========================================
echo    Pipeline completed successfully!
echo ========================================
echo.
echo Files generated:
echo   - cache\processed_data.csv
echo   - cache\daily_report.csv
echo   - cache\daily_analysis.csv
echo   - Various supporting JSON files
echo.
pause
