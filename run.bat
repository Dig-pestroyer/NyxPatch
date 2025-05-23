@echo off
echo Starting NyxPatcher...
echo.

:: Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python 3.7 or higher and try again.
    goto end
)

:: Run the NyxPatcher tool as a module
echo Running mod checker with direct .jar download links in report...
python -m data %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo NyxPatcher encountered an error. Please check the logs above.
    echo If the issue persists, please report it on the project's issue tracker.
) else (
    echo.
    echo NyxPatcher completed successfully.
    echo The update report includes direct download links to .jar files.
)

:end
pause

