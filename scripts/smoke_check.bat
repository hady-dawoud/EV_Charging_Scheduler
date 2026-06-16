@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

python -m pytest tests\grid_advisory tests\rl_feeder tests\rl_training -q

if "%FEEDER_RL_DATA_DIR%"=="" set FEEDER_RL_DATA_DIR=%REPO_ROOT%\..\..\..\outputs\evside_feeder_rl
if exist "%FEEDER_RL_DATA_DIR%\feeder_ev_action_catalog.parquet" (
  python scripts\rl_training\train_maskable_ppo_feeder_station_selector.py ^
    --feeder-rl-data-dir "%FEEDER_RL_DATA_DIR%" ^
    --grid-advisory-mode disabled ^
    --scenario-count 2 ^
    --duration-hours 1 ^
    --dry-run
) else (
  echo Skipping feeder RL dry-run; set FEEDER_RL_DATA_DIR to a restored feeder RL export package.
)
