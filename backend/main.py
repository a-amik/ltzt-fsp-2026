"""Запуск API для разработки: `uv run python main.py`."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("razryad.main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["razryad"])
