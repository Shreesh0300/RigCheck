@echo off
title RigCheck Runner
cls
echo ======================================================================
echo                 RigCheck Local Server Startup Script
echo ======================================================================
echo.
echo This script will spin up both the FastAPI backend and Vite frontend
echo in separate windows so you can run the full React dashboard locally.
echo.

REM Check if venv directory exists
if not exist "venv\" (
    echo [WARNING] virtual environment 'venv' folder not found!
    echo Creating virtual environment...
    python -m venv venv
)

REM Start Backend
echo [1/2] Starting FastAPI Backend on port 8000...
start "RigCheck Backend (Port 8000)" cmd /k "echo Activating virtual environment... && call venv\Scripts\activate && echo Installing/Verifying Python dependencies... && pip install -r requirements.txt && echo Starting FastAPI server... && uvicorn app:app --reload --host 127.0.0.1 --port 8000"

REM Check if node_modules exists
if not exist "node_modules\" (
    echo [INFO] node_modules not found. Running npm install...
    call npm install
)

REM Start Frontend
echo [2/2] Starting Vite Frontend on port 5173...
start "RigCheck Frontend (Port 5173)" cmd /k "echo Starting Vite React Dev Server... && npm run dev"

echo.
echo ======================================================================
echo SUCCESS: Both servers have been launched in separate windows!
echo ======================================================================
echo.
echo  - FastAPI Backend API:   http://127.0.0.1:8000
echo  - React Dashboard (Vite): http://127.0.0.1:5173
echo.
echo Feel free to close this main window. Keep the newly opened ones active.
echo ======================================================================
echo.
pause
