@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

if "%FEEDER_RL_DATA_DIR%"=="" set FEEDER_RL_DATA_DIR=%REPO_ROOT%\..\..\..\outputs\evside_feeder_rl
if "%SCENARIO_COUNT%"=="" set SCENARIO_COUNT=512
if "%DURATION_HOURS%"=="" set DURATION_HOURS=24
if "%TOTAL_TIMESTEPS%"=="" set TOTAL_TIMESTEPS=2000000
if "%CHECKPOINT_FREQ%"=="" set CHECKPOINT_FREQ=50000

python scripts\rl_training\train_maskable_ppo_feeder_station_selector.py ^
  --feeder-rl-data-dir "%FEEDER_RL_DATA_DIR%" ^
  --output-dir models\rl_feeder_final ^
  --tensorboard-log outputs\rl_feeder\tensorboard_final ^
  --grid-advisory-mode recorded ^
  --grid-evaluation-mode replay ^
  --request-prior-sources dundee,acn,digitaltwin ^
  --min-truth-level area_pf ^
  --exclude-adapter-proxy ^
  --require-replay-covered-area ^
  --scenario-count %SCENARIO_COUNT% ^
  --duration-hours %DURATION_HOURS% ^
  --total-timesteps %TOTAL_TIMESTEPS% ^
  --checkpoint-freq %CHECKPOINT_FREQ%
