@echo off
echo Checking for duplicate files...

REM Remove duplicate Python cache files
if exist "__pycache__" (
    echo Removing __pycache__ directories...
    for /d /r . %%d in (*__pycache__*) do (
        if exist "%%d" (
            echo Removing %%d
            rmdir /s /q "%%d" 2>nul
        )
    )
)

REM Remove .pyc files
echo Removing .pyc files...
for /r . %%f in (*.pyc) do (
    if exist "%%f" (
        echo Removing %%f
        del "%%f" 2>nul
    )
)

REM Remove temporary log files older than 7 days
if exist "logs" (
    echo Cleaning old log files...
    forfiles /p logs /s /m *.log /d -7 /c "cmd /c echo Deleting @path && del @path" 2>nul
)

echo Cleanup completed.