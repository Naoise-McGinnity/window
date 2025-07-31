@echo off

REM Try python
python --version >nul 2>&1
if errorlevel 0 (
    set PYTHON=python
) else (
    REM Try python3
    python3 --version >nul 2>&1
    if errorlevel 0 (
        set PYTHON=python3
    ) else (
        echo Python is not installed or not added to PATH.
        echo Please install Python from https://www.python.org/downloads/ and make sure to check "Add Python to PATH" during installation.
        pause
        exit /b
    )
)

REM Create virtual environment if missing
if not exist ".venv" (
    echo Creating virtual environment...
    %PYTHON% -m venv .venv
)

echo Activating virtual environment and installing requirements...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt

echo Running the game...
.venv\Scripts\python.exe 2d.py

pause