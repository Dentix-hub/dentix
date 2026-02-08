@echo off
setlocal

:: --- SAFETY START ---
cd /d "%~dp0"
echo Working from: %CD%
:: --------------------

echo ========================================================
echo FIX VERCEL BUILD FAILURE - LanguageContext Import Error
echo ========================================================
echo.

:: --- FILE CHECKS ---
if exist "frontend\src\context\LanguageContext.jsx" (
    echo [OK] Found LanguageContext.jsx
) else (
    echo [ERROR] LanguageContext.jsx missing!
    pause
    goto end_script
)

echo.
echo [STEP: Git Rename]
:: Just run the commands blindly for safety, ignore errors if already correct
git mv frontend/src/context/languageContext.jsx frontend/src/context/LanguageContext.tmp >nul 2>&1
git mv frontend/src/context/LanguageContext.tmp frontend/src/context/LanguageContext.jsx >nul 2>&1
echo [Git Rename] Attempted casing fix.

echo.
echo [STEP: Local Build]
echo Running npm build in frontend...
cd frontend
call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] Build failed! Check errors above.
    cd ..
    pause
    goto end_script
)
cd ..
echo [SUCCESS] Local build passed.

echo.
echo [STEP: Select Branch]
echo [1] Staging
echo [2] Main
set /p B_CHOICE="Branch (1/2): "

if "%B_CHOICE%"=="1" set T_BRANCH=staging
if "%B_CHOICE%"=="2" set T_BRANCH=main
if not defined T_BRANCH (
    echo Invalid branch.
    pause
    goto end_script
)

echo.
echo [STEP: Platform]
echo [1] GitHub Only
echo [2] Hugging Face Only
echo [3] Both
set /p P_CHOICE="Platform (1/2/3): "

if "%P_CHOICE%"=="1" goto do_github
if "%P_CHOICE%"=="2" goto do_hf
if "%P_CHOICE%"=="3" goto do_both

echo Invalid platform.
pause
goto end_script

:do_github
echo.
echo [GITHUB] Pushing to %T_BRANCH%...
git push origin %T_BRANCH%
if %ERRORLEVEL% NEQ 0 ( echo [ERROR] Push Failed. & pause & goto end_script )
echo [SUCCESS] GitHub Push Complete.
goto end_script

:do_hf
echo.
echo [HF] Preparing Backend Push...
git branch -D deploy-hf-backend >nul 2>&1
git checkout -b deploy-hf-backend

if exist "frontend" (
    git rm -r frontend >nul 2>&1
    git commit -m "chore: remove frontend" >nul 2>&1
)

echo [HF] Pushing to hf-staging...
git push hf-staging deploy-hf-backend:main -f
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] HF Push Failed.
    git checkout %T_BRANCH%
    pause
    goto end_script
)

echo [SUCCESS] HF Push Complete.
git checkout %T_BRANCH%
git branch -D deploy-hf-backend >nul 2>&1
goto end_script

:do_both
echo.
echo === DEPLOYING GITHUB ===
git push origin %T_BRANCH%
if %ERRORLEVEL% NEQ 0 ( echo [ERROR] Github Fail. & pause & goto end_script )

echo.
echo === DEPLOYING HF ===
git branch -D deploy-hf-backend >nul 2>&1
git checkout -b deploy-hf-backend

if exist "frontend" (
    git rm -r frontend >nul 2>&1
    git commit -m "chore: remove frontend" >nul 2>&1
)

git push hf-staging deploy-hf-backend:main -f
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] HF Fail.
    git checkout %T_BRANCH%
    pause
    goto end_script
)

git checkout %T_BRANCH%
git branch -D deploy-hf-backend >nul 2>&1
echo [SUCCESS] Both deployed.
goto end_script

:end_script
echo.
echo [DONE] Script finished.
pause
exit /b
