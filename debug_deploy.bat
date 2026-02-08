@echo off
echo ===========================================
echo   MANUAL DEPLOYMENT DEBUGGER
echo ===========================================
echo.
echo 1. Checking Git Status...
git status
echo.
echo 2. Adding all files...
git add .
echo.
echo 3. Committing changes...
git commit -m "Manual Fix: Update frontend and config"
echo.
echo 4. Pushing to GitHub (Staging)...
git push origin staging
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Push Failed! See message above.
) ELSE (
    echo.
    echo [SUCCESS] Push Completed!
)
echo.
echo ===========================================
pause
