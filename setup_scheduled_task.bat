@echo off
chcp 65001 >nul
echo.
echo ================================================
echo   Setting up Daily GEX Dashboard Scheduled Task
echo   Runs at 15:30 local time (9:30 AM New York)
echo ================================================
echo.

cd /d "%~dp0"

:: Create Streamlit config to skip email prompt
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"

echo [general] > "%USERPROFILE%\.streamlit\credentials.toml"
echo email = "" >> "%USERPROFILE%\.streamlit\credentials.toml"

echo [server] > "%USERPROFILE%\.streamlit\config.toml"
echo headless = false >> "%USERPROFILE%\.streamlit\config.toml"
echo. >> "%USERPROFILE%\.streamlit\config.toml"
echo [browser] >> "%USERPROFILE%\.streamlit\config.toml"
echo gatherUsageStats = false >> "%USERPROFILE%\.streamlit\config.toml"

:: Register the scheduled task
powershell -Command ^
  "$action = New-ScheduledTaskAction -Execute '%~dp0auto_launch.bat' -WorkingDirectory '%~dp0';" ^
  "$trigger = New-ScheduledTaskTrigger -Daily -At '15:30';" ^
  "$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -WakeToRun;" ^
  "Register-ScheduledTask -TaskName 'GEX Dashboard - NY Open' -Action $action -Trigger $trigger -Settings $settings -Description 'Auto-launch GEX Dashboard at New York market open (9:30 AM ET)' -Force"

echo.
echo ================================================
echo   Scheduled task created!
echo   Name:  GEX Dashboard - NY Open
echo   Time:  15:30 daily (9:30 AM New York)
echo   Action: Opens dashboard + auto-fetches data
echo ================================================
echo.
pause
