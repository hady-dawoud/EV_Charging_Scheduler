@echo off
setlocal

if "%TENSORBOARD_PORT%"=="" set TENSORBOARD_PORT=6007
tensorboard.exe --logdir outputs\rl_feeder\tensorboard_final --port %TENSORBOARD_PORT%
