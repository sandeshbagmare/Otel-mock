@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title mockotel - mock OpenTelemetry providers

rem --- find a Python launcher ---------------------------------------------
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY ( where python >nul 2>nul && set "PY=python" )

:menu
cls
echo ============================================================
echo            mockotel : mock OpenTelemetry providers
echo ============================================================
echo.
echo   [1]  Quick start  ^(Python, no install^)  - pick providers ^& ports
echo   [2]  Start ALL providers + dashboard on default ports
echo   [3]  Docker full stack ^(adds real OTEL Collector :4317/:4318^)
echo   [4]  Docker + REAL backends ^(Jaeger, Zipkin, Prometheus, Grafana^)
echo   [5]  Send sample telemetry to all providers
echo   [6]  Replay saved captures to a provider
echo   [7]  List providers
echo   [0]  Exit
echo.
set /p choice="  Choose [1]: "
if "%choice%"=="" set choice=1

if "%choice%"=="1" goto quick
if "%choice%"=="2" goto all
if "%choice%"=="3" goto docker
if "%choice%"=="4" goto dockerreal
if "%choice%"=="5" goto sample
if "%choice%"=="6" goto replay
if "%choice%"=="7" goto list
if "%choice%"=="0" goto end
goto menu

:quick
if not defined PY goto nopy
%PY% -m mockotel
goto done

:all
if not defined PY goto nopy
%PY% -m mockotel --all
goto done

:docker
where docker >nul 2>nul || ( echo. & echo   Docker not found. Install Docker Desktop first. & pause & goto menu )
echo.
echo   Building and starting the Docker stack (Ctrl+C to stop)...
docker compose -f docker/docker-compose.yml up --build
goto done

:dockerreal
where docker >nul 2>nul || ( echo. & echo   Docker not found. Install Docker Desktop first. & pause & goto menu )
echo.
echo   Mocks + real backends. UIs: Jaeger :16686  Zipkin :9411  Prometheus :9090  Grafana :3000
docker compose -f docker/docker-compose.yml -f docker/real-backends.yml up --build
goto done

:sample
if not defined PY goto nopy
%PY% examples\send_test_telemetry.py --all
echo.
pause
goto menu

:replay
if not defined PY goto nopy
set /p rport="  Replay captures to which provider port? [5001]: "
if "%rport%"=="" set rport=5001
%PY% examples\replay.py --to http://localhost:%rport%
echo.
pause
goto menu

:list
if not defined PY goto nopy
%PY% -m mockotel --list
echo.
pause
goto menu

:nopy
echo.
echo   Python was not found on your PATH.
echo   Install Python 3.8+ from https://www.python.org/downloads/ (tick "Add to PATH"),
echo   or use option [3] Docker instead.
echo.
pause
goto menu

:done
echo.
pause
:end
endlocal
