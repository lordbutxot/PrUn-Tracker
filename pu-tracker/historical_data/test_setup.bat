@echo off
echo Testing Python installation...
echo.

python --version
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

echo Python found! ✓
echo.

echo Testing Python modules...
python -c "import sys; print('Python path:', sys.executable)"
python -c "import pandas; print('Pandas:', pandas.__version__)" 2>nul
if %errorlevel% neq 0 (
    echo WARNING: pandas not found - some features may not work
) else (
    echo Pandas found! ✓
)

echo.
echo Testing file structure...
if exist "historical_data\main.py" (
    echo historical_data\main.py exists ✓
) else (
    echo ERROR: historical_data\main.py not found!
)

if exist "cache" (
    echo cache directory exists ✓
) else (
    echo WARNING: cache directory not found
    mkdir cache
    echo Created cache directory
)

if exist "logs" (
    echo logs directory exists ✓
) else (
    echo Created logs directory
    mkdir logs
)

echo.
echo Setup test completed!
pause