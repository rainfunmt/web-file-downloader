@echo off
rem Build dist\WebFileDownloader.exe (Windows).
rem Usage: double-click this file, or run "build_exe.bat" in this folder.
setlocal
cd /d "%~dp0"

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv || goto :error
)
echo Installing PyInstaller...
.venv\Scripts\python -m pip install -q --disable-pip-version-check pyinstaller || goto :error

rem Python 3.13.0 venvs cannot find Tcl/Tk, so PyInstaller would drop tkinter.
rem Point Tcl/Tk at the base Python installation.
for /f "delims=" %%i in ('python -c "import sys; print(sys.base_prefix)"') do set "PYBASE=%%i"
for /d %%d in ("%PYBASE%\tcl\tcl8*") do set "TCL_LIBRARY=%%d"
for /d %%d in ("%PYBASE%\tcl\tk8*") do set "TK_LIBRARY=%%d"

echo Building, this takes about a minute...
.venv\Scripts\python -m PyInstaller --noconfirm --clean --onefile --windowed --name WebFileDownloader gui.py || goto :error

echo.
echo Done! Output: dist\WebFileDownloader.exe
goto :eof

:error
echo.
echo Build failed. See the messages above.
exit /b 1
