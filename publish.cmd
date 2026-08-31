@echo off
setlocal

rem Uploads one release to PyPI, e.g.  publish.cmd 0.8.0
rem
rem Takes the version explicitly because dist\ keeps every earlier build, and
rem PyPI rejects a file that has already been published - so an unscoped
rem "twine upload dist\*" fails on the old files before reaching the new ones.
rem
rem Publish this package BEFORE thonny-lahendus: the plugin's metadata
rem requires the matching easy-py version.

if "%~1"=="" (
    echo Usage: publish.cmd VERSION
    echo   e.g. publish.cmd 0.8.0
    exit /b 1
)

set "PY=py -3"
where py >nul 2>&1 || set "PY=python"

set "PKG=dist\easy_py-%~1"

if not exist "%PKG%-py3-none-any.whl" (
    echo No build for %~1 in dist\ - run build.cmd first.
    exit /b 1
)

%PY% -m twine --version >nul 2>&1 || %PY% -m pip install --upgrade twine || goto :failed

%PY% -m twine check "%PKG%*" || goto :failed
%PY% -m twine upload "%PKG%*" || goto :failed
exit /b 0

:failed
echo.
echo Publish failed.
exit /b 1
