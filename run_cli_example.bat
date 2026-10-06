@echo off
title UNR Tool v1 - CLI Example
cd /d "%~dp0"

echo Running CLI example on 11_21.unr...
echo.

python cli.py --unr "..\..\12-Reverse-Engineering\outputs\giranforge-gfe1-trace-lab-v9\Giran Forge\Maps\11_21.unr" --client "..\..\12-Reverse-Engineering\outputs\giranforge-gfe1-trace-lab-v9\Giran Forge" --output "output_11_21" --copy

echo.
echo Check the output_11_21 folder for results and HTML report.
pause
