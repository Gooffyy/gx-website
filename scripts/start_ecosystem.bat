@echo off
title GX MENU Ecosystem Launcher
color 0b
echo ========================================================
echo        GX MENU - SERVER & DISCORD BOT LAUNCHER
echo ========================================================
echo.

cd /d "%~dp0\.."

:: Auto-detect Node.js executable
set "NODE_BIN=node"

where node >nul 2>nul
if %errorlevel% neq 0 (
    if exist "%LOCALAPPDATA%\Programs\Kimi\resources\resources\runtime\node.exe" (
        set "NODE_BIN=%LOCALAPPDATA%\Programs\Kimi\resources\resources\runtime\node.exe"
    ) else if exist "C:\Program Files\nodejs\node.exe" (
        set "NODE_BIN=C:\Program Files\nodejs\node.exe"
    ) else if exist "C:\Program Files (x86)\nodejs\node.exe" (
        set "NODE_BIN=C:\Program Files (x86)\nodejs\node.exe"
    ) else (
        echo [ERROR] Node.js executable not found!
        echo Please download and install Node.js from: https://nodejs.org/
        pause
        exit /b 1
    )
)

echo [OK] Using Node runtime: "%NODE_BIN%"
echo.

echo [1/2] Starting Web Server on Port 8080 (Client Portal & Admin Console)...
start "GX Web Server" cmd /k "title GX Server && ^"%NODE_BIN%^" server/server.js"

timeout /t 2 /nobreak >nul

echo [2/2] Starting Discord Bot with Cloudflare Auth & Components V2...
start "GX Discord Bot" cmd /k "title GX Discord Bot && ^"%NODE_BIN%^" bot/bot.js"

echo.
echo ========================================================
echo   Both services are now running in separate windows!
echo   - Web Server:     http://localhost:8080
echo   - Client Portal:  http://localhost:8080/dashboard.html
echo   - Admin Console:  http://localhost:8080/admin.html
echo ========================================================
pause
