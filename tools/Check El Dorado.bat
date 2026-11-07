@echo off
rem El Dorado's health check: whether the install is whole and how the games ran (read only).
rem The page opens in the browser: analysis\health-report.html
cd /d "%~dp0"
"python\python.exe" "tools\health_check.py" %*
