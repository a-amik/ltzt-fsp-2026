"""Слой провайдера языковой модели.

Всё, что сервис просит у модели, проходит здесь и имеет заглушку на правилах,
поэтому сервис работает без ключа. Провайдер выбирается настройкой RZ_LLM_PROVIDER:
stub (по умолчанию); провайдеры с ключом (YandexGPT, GigaChat) — после MVP. Что и зачем вызывается — раздел
документации «Языковые модели». Данные кандидата уходят провайдеру только те,
что кандидат одобрил к показу.
"""
from __future__ import annotations

import re

from ..config import settings
from . import docs as _docs
from .scoring import parse_need as _rule_parse_need


class Provider:
    name = "stub"

    def parse_need(self, text: str) -> dict:
        return _rule_parse_need(text)

    def parse_resume(self, text: str) -> dict:
        """Поля резюме с меткой «со слов»: имя, специализация, стек, стаж, места работы, ожидания, формат."""
        return _docs.parse_resume(text)

    def parse_vacancy(self, text: str) -> dict:
        """Текст своей вакансии компании — в поля формы."""
        return _docs.parse_vacancy(text)

    def grade_open(self, text: str, rubric: list[str], keys: list[list[str]]) -> dict:
        t = text.lower()
        hits = [any(k in t for k in ks) for ks in keys]
        return {"score": sum(hits) / len(rubric), "hits": hits, "confident": len(text.strip()) > 60}

    def rephrase(self, steps: list[dict]) -> list[dict]:
        """Реплики агентов живее. Заглушка возвращает как есть."""
        return steps


def get_provider() -> Provider:
    # Провайдеры с ключом подключаются здесь той же сигнатурой; без ключа — заглушка.
    return Provider()


provider = get_provider()
PROVIDER_INFO = {"configured": settings.llm_provider, "active": provider.name}
