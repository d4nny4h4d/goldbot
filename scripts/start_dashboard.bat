@echo off
echo ========================================
echo  AhadAI Trading Hub
echo ========================================
echo.

cd /d "%~dp0.."

call goldbot_env\Scripts\activate.bat

echo Starting Streamlit dashboard at http://localhost:8501
echo Press Ctrl+C to stop
echo.

streamlit run dashboard/dashboard.py --server.port 8501

pause
