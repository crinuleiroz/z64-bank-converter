@echo off
setlocal

:: Check the number of files in the input
if "%~2"=="" (
  :: Single file
  python "Zelda64 Bank Converter.py" "%~1" -g oot
) else (
  :: Two files
  python "Zelda64 Bank Converter.py" "%~1" "%~2" -g oot -o xml
)

endlocal
pause
