@echo off
setlocal

python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e packages\ev_core

echo Setup complete. Activate with: .venv\Scripts\activate.bat
