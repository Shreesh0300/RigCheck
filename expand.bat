@echo off
echo Starting fetch...
python steam\fetch_250_raw.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo Starting 04...
python steam\04_normalize_requirements.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo Starting 05...
python steam\05_map_hardware_tiers.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo Starting 06...
python steam\06_enrich_database.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo Starting 07...
python steam\07_fix_prices.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo Starting merge...
python steam\merge_250_processed.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo Starting build search metadata...
python build_search_metadata.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo DONE!
