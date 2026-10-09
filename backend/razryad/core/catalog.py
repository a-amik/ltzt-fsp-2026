"""Справочник: специализации, грейды, навыки. Составлен командой, как разрешает ТЗ."""

SPECS = [
    {"id": "backend", "name": "Бэкенд", "stack": ["Python", "Go", "Java", "PostgreSQL", "Kafka", "Redis", "Docker"]},
    {"id": "frontend", "name": "Фронтенд", "stack": ["TypeScript", "React", "Vue", "Next.js", "CSS", "Webpack"]},
    {"id": "mobile", "name": "Мобильная разработка", "stack": ["Kotlin", "Swift", "Flutter", "React Native"]},
    {"id": "data", "name": "Анализ данных", "stack": ["SQL", "Python", "ClickHouse", "Airflow", "Tableau"]},
    {"id": "ml", "name": "Машинное обучение", "stack": ["Python", "PyTorch", "scikit-learn", "CUDA", "MLflow"]},
    {"id": "devops", "name": "DevOps", "stack": ["Kubernetes", "Terraform", "Linux", "Ansible", "Prometheus"]},
]
SPEC_IDS = [s["id"] for s in SPECS]

# Грейд — отрезок на шкале оценки навыка θ; границы — середины между ступенями.
GRADES = [
    {"id": 0, "name": "Стажёр", "short": "Intern", "lo": -9.0, "hi": -1.5},
    {"id": 1, "name": "Младший", "short": "Junior", "lo": -1.5, "hi": -0.5},
    {"id": 2, "name": "Средний", "short": "Middle", "lo": -0.5, "hi": 0.5},
    {"id": 3, "name": "Старший", "short": "Senior", "lo": 0.5, "hi": 1.5},
    {"id": 4, "name": "Ведущий", "short": "Lead", "lo": 1.5, "hi": 9.0},
]
GRADE_MID = [-2.0, -1.0, 0.0, 1.0, 2.0]

SKILLS = {
    "backend": ["Алгоритмы", "Базы данных", "Конкурентность", "Сети и API", "Проектирование"],
    "frontend": ["Алгоритмы", "Язык и типы", "Рендеринг", "Сети и API", "Проектирование"],
    "mobile": ["Алгоритмы", "Платформа", "Конкурентность", "Сети и API", "Проектирование"],
    "data": ["SQL", "Статистика", "Пайплайны", "Моделирование данных", "Визуализация"],
    "ml": ["Математика", "Классический ML", "Глубокое обучение", "Данные", "Продакшен ML"],
    "devops": ["Linux", "Сети", "Контейнеры", "Наблюдаемость", "Инфраструктура как код"],
}

WORK_FORMATS = ["офис", "гибрид", "удалённо"]
DECLINE_REASONS = ["мало денег", "не тот стек", "формат", "не ищу сейчас", "компания не интересна"]


def grade_of(theta: float) -> int:
    for g in GRADES:
        if g["lo"] <= theta < g["hi"]:
            return g["id"]
    return 4 if theta >= 0 else 0


def spec(spec_id: str) -> dict:
    return next(s for s in SPECS if s["id"] == spec_id)
