@echo off
chcp 65001 >nul

:: Kill any existing Streamlit processes to avoid port conflicts
taskkill /F /IM streamlit.exe >nul 2>&1

:: Wait a moment for port to free up
timeout /t 2 /nobreak >nul

cd /d "C:\Users\Wko\Desktop\Tastytrade-API-GEX-Dashboard"

:: Launch dashboard (auto-opens browser at localhost:8501)
python -m streamlit run simple_dashboard.py --server.headless false --browser.gatherUsageStats false
