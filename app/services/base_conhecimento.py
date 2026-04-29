import json
from difflib import get_close_matches
from app.config import settings

with open(settings.KNOWLEDGE_BASE_FILE, "r", encoding="utf-8") as f:
    KNOWLEDGE_BASE = json.load(f)


def find_answer(question: str, cutoff: float = 0.4) -> str:
    questions = list(KNOWLEDGE_BASE.keys())
    matches = get_close_matches(question, questions, n=1, cutoff=cutoff)
    if matches:
        return KNOWLEDGE_BASE[matches[0]]
    return "Desculpe, não encontrei uma resposta. Abra um chamado para obter ajuda."
