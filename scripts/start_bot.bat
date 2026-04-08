@echo off
echo ========================================
echo  GoldBot - Automated XAU/USD Trading
echo ========================================
echo.

cd /d "%~dp0.."

echo Activating virtual environment...
call goldbot_env\Scripts\activate.bat

echo Starting GoldBot...
echo Press Ctrl+C to stop
echo.

python src/main.py --config config/strategies.yaml --env .env

pause
