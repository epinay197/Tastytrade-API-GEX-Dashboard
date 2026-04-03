@echo off
chcp 65001 >nul

:: Skip launch if US markets are closed today (weekend or holiday)
powershell -NoProfile -Command ^
  "$et=[System.TimeZoneInfo]::ConvertTimeFromUtc([DateTime]::UtcNow,[System.TimeZoneInfo]::FindSystemTimeZoneById('Eastern Standard Time')).Date;" ^
  "if($et.DayOfWeek-eq'Saturday'-or$et.DayOfWeek-eq'Sunday'){exit 1};" ^
  "$h=@('2025-01-01','2025-01-20','2025-02-17','2025-04-18','2025-05-26','2025-06-19','2025-07-04','2025-09-01','2025-11-27','2025-12-25','2026-01-01','2026-01-19','2026-02-16','2026-04-03','2026-05-25','2026-06-19','2026-07-03','2026-09-07','2026-11-26','2026-12-25','2027-01-01','2027-01-18','2027-02-15','2027-03-26','2027-05-31','2027-06-18','2027-07-05','2027-09-06','2027-11-25','2027-12-24');" ^
  "if($h-contains$et.ToString('yyyy-MM-dd')){exit 1};exit 0"
if errorlevel 1 (
    echo US markets closed today — skipping GEX Tastytrade launch.
    exit /b 0
)

:: Kill any existing Streamlit processes to avoid port conflicts
taskkill /F /IM streamlit.exe >nul 2>&1

:: Wait a moment for port to free up
timeout /t 2 /nobreak >nul

cd /d "C:\Users\Wko\Desktop\Tastytrade-API-GEX-Dashboard"

:: Launch dashboard (auto-opens browser at localhost:8501)
python -m streamlit run simple_dashboard.py --server.headless false --browser.gatherUsageStats false
