import asyncio
import json
import random
import re
from pathlib import Path
from typing import Dict, List, Tuple

DATA_DIR = Path("data")
MEMORY_FILE = DATA_DIR / "memory.json"
MAX_WORDS_PER_USER = 5000
ALLOW_APOSTROPHES = True

_file_lock = asyncio.Lock()
_WORD_RE = re.compile(r"[A-Za-z0-9]+'?[A-Za-z0-9]+" if ALLOW_APOSTROPHES else r"[A-Za-z0-9]+")

def _sanitize_words(text: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]

async def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

async def _read_json() -> Dict[str, List[str]]:
    if not MEMORY_FILE.exists():
        return {}
    def _read():
        with MEMORY_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return await asyncio.to_thread(_read)

async def _write_json(data: Dict[str, List[str]]) -> None:
    def _write():
        with MEMORY_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    await asyncio.to_thread(_write)

async def add_message_words(user_id: str, message_text: str) -> List[str]:
    words = _sanitize_words(message_text)
    if not words:
        return []

    await _ensure_data_dir()
    async with _file_lock:
        memory = await _read_json()
        arr = memory.get(user_id, [])
        arr.extend(words)
        if len(arr) > MAX_WORDS_PER_USER:
            arr = arr[-MAX_WORDS_PER_USER:]
        memory[user_id] = arr
        await _write_json(memory)
    return words

async def get_all_words() -> List[str]:
    await _ensure_data_dir()
    async with _file_lock:
        memory = await _read_json()
    all_words = []
    for wlist in memory.values():
        all_words.extend(wlist)
    return all_words

# ------------------------------
# 🔹 Markov chain generator
# ------------------------------

def build_markov_chain(words: List[str]) -> Dict[str, List[str]]:
    """markov map"""
    chain: Dict[str, List[str]] = {}
    for i in range(len(words) - 1):
        w, nxt = words[i], words[i+1]
        chain.setdefault(w, []).append(nxt)
    return chain

def make_sentence(words: List[str], min_len: int = 5, max_len: int = 15) -> str:
    """markov chain"""
    if len(words) < 2:
        return "..."

    chain = build_markov_chain(words)
    length = random.randint(min_len, max_len)

    # random start word not dependant
    word = random.choice(words)
    sentence = [word]

    for _ in range(length - 1):
        next_words = chain.get(word)
        if not next_words:
            word = random.choice(words)  # jump to random word if dead end
        else:
            word = random.choice(next_words)
        sentence.append(word)

    text = " ".join(sentence)
    return text.capitalize() + "."
