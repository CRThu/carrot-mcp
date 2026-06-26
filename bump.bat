@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   Carrot MCP - Version Bump ^& Release
echo ========================================
echo.

if "%~1" neq "" (
    set PKG_NAME=%~1
    goto :skip_menu
)

echo [0] carrot-mcp (main)

set IDX=1
for /d %%D in (packages\carrot-mcp-*) do (
    set "PKG_DIR=%%D"
    set "PKG_DIR=!PKG_DIR:packages\=!"
    echo [!IDX!] !PKG_DIR!
    set /a IDX+=1
)

set /a MAX_IDX=%IDX%-1
echo.
set /p PKG="Select package (0-%MAX_IDX%): "

if "!PKG!"=="0" (
    set PKG_NAME=carrot-mcp
) else (
    set IDX=1
    for /d %%D in (packages\carrot-mcp-*) do (
        if "!IDX!"=="!PKG!" (
            set "PKG_DIR=%%D"
            set "PKG_NAME=!PKG_DIR:packages\=!"
        )
        set /a IDX+=1
    )
)

if not defined PKG_NAME (
    echo Invalid selection
    exit /b 1
)

:skip_menu
echo.
if "%PKG_NAME%"=="carrot-mcp" (
    for /f "tokens=*" %%i in ('uv version --short') do set CUR_VER=%%i
) else (
    for /f "tokens=*" %%i in ('uv version --short --package %PKG_NAME%') do set CUR_VER=%%i
)

for /f "tokens=1,2,3 delims=." %%a in ("%CUR_VER%") do (
    set MAJOR=%%a
    set MINOR=%%b
    set PATCH=%%c
)

set /a NEW_PATCH_NUM=%PATCH%+1
set NEW_PATCH=%MAJOR%.%MINOR%.%NEW_PATCH_NUM%

set /a NEW_MINOR_NUM=%MINOR%+1
set NEW_MINOR=%MAJOR%.%NEW_MINOR_NUM%.0

set /a NEW_MAJOR_NUM=%MAJOR%+1
set NEW_MAJOR=%NEW_MAJOR_NUM%.0.0

echo Current: %PKG_NAME% %CUR_VER%
echo.
echo Bump type:
echo [1] patch: %CUR_VER% -^> %NEW_PATCH%
echo [2] minor: %CUR_VER% -^> %NEW_MINOR%
echo [3] major: %CUR_VER% -^> %NEW_MAJOR%
echo.
set /p TYPE="Select type (1-3): "

if "%TYPE%"=="1" (set BUMP=patch)
if "%TYPE%"=="2" (set BUMP=minor)
if "%TYPE%"=="3" (set BUMP=major)

if not defined BUMP (
    echo Invalid selection
    exit /b 1
)

if "%BUMP%"=="patch" (set EXPECTED=%NEW_PATCH%)
if "%BUMP%"=="minor" (set EXPECTED=%NEW_MINOR%)
if "%BUMP%"=="major" (set EXPECTED=%NEW_MAJOR%)

echo.
echo Package: %PKG_NAME%
echo Version: %CUR_VER% -^> %EXPECTED%
echo.

set /p CONFIRM="Confirm? (y/n): "
if not "!CONFIRM!"=="y" (
    echo Cancelled
    exit /b 0
)

echo.
echo Bumping version...
if "%PKG_NAME%"=="carrot-mcp" (
    uv version --bump %BUMP%
) else (
    uv version --bump %BUMP% --package %PKG_NAME%
)

echo.
echo %PKG_NAME%: %CUR_VER% -^> %EXPECTED%

echo.
echo Git commit and tag? (y/n)
set /p DO_GIT=": "

if "!DO_GIT!"=="y" (
    git add -A
    git commit -m "release: %PKG_NAME% %EXPECTED%"
    
    echo Tagging: %PKG_NAME%@%EXPECTED%
    git tag %PKG_NAME%@%EXPECTED%
    echo.
    echo Done! Push with: git push --tags
) else (
    echo.
    echo Done! Version bumped. Commit manually.
)

endlocal
