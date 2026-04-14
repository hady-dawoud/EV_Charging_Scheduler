## API local setup

Run the API from this folder:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful URLs:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

If you need to create the virtual environment first:

```powershell
uv venv .venv --python 3.12
.venv\Scripts\python.exe -m pip install fastapi "uvicorn[standard]"
```
