@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul

set "WAD_DIR=examples\benchmark\output"
set "VIZDOOM=examples\play\vizdoom"
set "IWAD=examples\play\freedoom2.wad"

set "i=0"
for %%f in ("%WAD_DIR%\*.wad") do (
    set /a i+=1
    set "wads[!i!]=%%f"
    echo !i! %%f
)
set "total_wads=!i!"

if "!total_wads!"=="0" (
    echo No .wad files found in "%WAD_DIR%".
    popd >nul
    exit /b 1
)

:while_true
    REM read -r -p "Select a scenario..."
    set "choice="
    set /p "choice=Select a scenario (1-!total_wads!): "

    REM if input is empty, exit 0
    if "!choice!"=="" (
        echo.
        popd >nul
        exit /b 0
    )

    REM Validate if choice is numeric and within range
    REM (Batch hack to check if variable contains only numbers)
    for /f "delims=0123456789" %%a in ("!choice!") do goto while_true
    
    if !choice! geq 1 (
        if !choice! leq !total_wads! (
            REM wad="${wads[$((choice-1))]}"
            set "wad=!wads[%choice%]!"
            goto break
        )
    )
    goto while_true

:break

start "Host" "%VIZDOOM%" -windowed 1 -iwad "%IWAD%" -file "!wad!" -host 2

timeout /t 1 /nobreak >nul

start "Join" "%VIZDOOM%" -windowed 1 -iwad "%IWAD%" -file "!wad!" -join 127.0.0.1

for %%x in ("%VIZDOOM%") do set "VIZ_PROC=%%~nxx"
if /I "!VIZ_PROC!"=="vizdoom" set "VIZ_PROC=vizdoom.exe"
:wait_loop
timeout /t 1 /nobreak >nul
tasklist /FI "IMAGENAME eq !VIZ_PROC!" 2>NUL | find /I /N "!VIZ_PROC!">NUL
if "%ERRORLEVEL%"=="0" goto wait_loop

popd >nul
exit /b 0
