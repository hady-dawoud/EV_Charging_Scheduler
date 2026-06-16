@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

if "%FEEDER_RL_DATA_DIR%"=="" set FEEDER_RL_DATA_DIR=%REPO_ROOT%\..\..\..\outputs\evside_feeder_rl
if "%CHECKPOINT_PATH%"=="" set CHECKPOINT_PATH=%REPO_ROOT%\models\rl_feeder_final\maskable_ppo_feeder_station_selector.zip
if "%POLICY%"=="" set POLICY=checkpoint

python scripts\rl_training\evaluate_maskable_ppo_feeder_station_selector.py ^
  --feeder-rl-data-dir "%FEEDER_RL_DATA_DIR%" ^
  --checkpoint-path "%CHECKPOINT_PATH%" ^
  --policy %POLICY% ^
  --grid-advisory-mode recorded ^
  --grid-evaluation-mode replay ^
  --min-truth-level area_pf ^
  --exclude-adapter-proxy ^
  --require-replay-covered-area ^
  --output-json outputs\rl_feeder\evaluation_%POLICY%.json ^
  --output-csv outputs\rl_feeder\evaluation_runs.csv
