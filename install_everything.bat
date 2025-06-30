@echo off
REM SDRTrunk Monitor Full Installer

REM Check if python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python not found. Downloading and installing Python...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe' -OutFile 'python-installer.exe'"
    start /wait python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del python-installer.exe
    echo Python installed.
) else (
    echo Python is already installed.
)

REM Upgrade pip to latest
python -m pip install --upgrade pip

REM Install required Python packages
pip install -r requirements.txt

echo.
echo Installation complete. You can now run the monitor with: python sdrtrunk_monitor.py
pause 