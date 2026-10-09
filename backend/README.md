# Разряд — сервер

FastAPI + SQLAlchemy. База — PostgreSQL на стенде, SQLite для разработки и тестов.

```sh
uv sync                         # зависимости
uv run python -m razryad.seed   # синтетические кандидаты, работодатель, вакансии
uv run python main.py           # http://localhost:8000/docs — OpenAPI
uv run pytest                   # тесты ядра и сквозной сценарий
```

Настройки — переменные `RZ_*` (см. `razryad/config.py`): база, режим почты
(`screen` показывает код подтверждения в ответе), провайдер модели (`stub`
по умолчанию), адрес провайдера ФСП ID (мок внутри сервиса).
