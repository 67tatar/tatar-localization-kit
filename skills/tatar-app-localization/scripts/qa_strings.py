#!/usr/bin/env python3
"""QA-проверка татарской локализации UI-строк.

Сравнивает файл-источник и файл перевода с одинаковым набором ключей и
сообщает об:

  * расхождении наборов ключей (отсутствующие / лишние);
  * потерянных или изменённых плейсхолдерах ({name}, {0}, %s, %1$s, %(x)d);
  * непереведённых строках (перевод совпадает с исходной строкой и содержит буквы);
  * дубликатах (разные ключи получили одинаковый перевод);
  * пробелах по краям и управляющих символах;
  * аномальной длине (перевод сильно короче/длиннее источника);
  * нарушении глоссария (в источнике есть term, а татарский эквивалент в
    переводе не найден).

Форматы файлов: JSON (плоский или вложенный объект) и .properties.
Глоссарий: CSV с заголовком en,ru,tt[,note].

Коды возврата: 0 — чисто; 1 — ошибки; 2 — только предупреждения
(--strict превращает предупреждения в ошибки).

Пример:
    python qa_strings.py strings-ru.json strings-tt.json \
        --glossary ../data/glossary.csv --strict
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Буквенные классы: латиница + русская кириллица + татарские дополнительные буквы
LETTERS_RU = "А-Яа-яЁё"
LETTERS_TT = "әөүҗңһӘӨҮҖҢҺ"
LETTER_CLASS = f"A-Za-z{LETTERS_RU}{LETTERS_TT}"

# Плейсхолдеры: {name}, {0}, {}; C/Java/Qt: %s %d %1$s %1$@; Python: %(name)s
PLACEHOLDER_PATTERNS = [
    re.compile(r"\{[^{}]*\}"),
    re.compile(r"%(?:\d+\$)?[@sdfuxX]"),
    re.compile(r"%\(\w+\)[sdif]"),
]


def flatten(obj: object, prefix: str = "") -> Dict[str, object]:
    """Развернуть вложенный JSON-объект в плоский словарь 'a.b' -> значение."""
    out: Dict[str, object] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            out.update(flatten(v, key))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}.{i}"))
    else:
        out[prefix] = obj
    return out


def load_pairs(path: Path) -> Dict[str, str]:
    """Загрузить файл локализации (JSON или .properties) в плоский словарь."""
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        flat = flatten(data)
        return {k: "" if v is None else str(v) for k, v in flat.items()}
    # .properties: '#' или '!' — комментарий; разделитель '=' или ':'
    pairs: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line[0] in "#!":
            continue
        sep = "=" if "=" in line else (":" if ":" in line else None)
        if sep is None:
            continue
        key, value = line.split(sep, 1)
        pairs[key.strip()] = value.strip()
    return pairs


def load_glossary(path: Path) -> List[Dict[str, str]]:
    """CSV с заголовком en,ru,tt[,note]; кодировка UTF-8 (BOM допускается)."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def placeholders(s: str) -> List[str]:
    """Извлечь все плейсхолдеры из строки (список вхождений, не множество)."""
    found: List[str] = []
    for pat in PLACEHOLDER_PATTERNS:
        found.extend(m.group(0) for m in pat.finditer(s))
    return found


def has_letters(s: str) -> bool:
    return re.search(f"[{LETTER_CLASS}]", s) is not None


def contains_term(text: str, term: str) -> bool:
    """Поиск термина по границам слов; буквы двух алфавитов границей не считаются."""
    pattern = rf"(?<![{LETTER_CLASS}]){re.escape(term)}(?![{LETTER_CLASS}])"
    return re.search(pattern, text, re.IGNORECASE) is not None


def check(
    src: Dict[str, str],
    tgt: Dict[str, str],
    glossary: Optional[List[Dict[str, str]]] = None,
) -> Tuple[List[str], List[str]]:
    """Сравнить источник и перевод; вернуть (ошибки, предупреждения)."""
    errors: List[str] = []
    warnings: List[str] = []

    for k in sorted(set(src) - set(tgt)):
        errors.append(f"нет ключа в переводе: {k}")
    for k in sorted(set(tgt) - set(src)):
        errors.append(f"лишний ключ в переводе: {k}")

    common = set(src) & set(tgt)
    for k in sorted(common):
        s, t = src[k], tgt[k]
        # Плейсхолдеры: мультимножества должны совпадать
        ps, pt = Counter(placeholders(s)), Counter(placeholders(t))
        if ps != pt:
            errors.append(f"плейсхолдеры не совпадают: {k}: источник {dict(ps)} vs перевод {dict(pt)}")
        # Края и управляющие символы
        if t != t.strip():
            errors.append(f"пробелы по краям: {k}")
        if any(ord(c) < 32 and c not in "\t\n" for c in t):
            errors.append(f"управляющий символ: {k}")
        # Пустой перевод при непустом источнике
        if has_letters(s) and not t.strip():
            errors.append(f"пустой перевод: {k}")
        # Непереведённое: перевод совпал с источником, хотя в нём есть буквы
        if s == t and has_letters(t):
            warnings.append(f"не переведено (совпадает с источником): {k}: {t!r}")
        # Аномальная длина (только для строк с буквами, источник не короче 8 знаков)
        if has_letters(s) and has_letters(t) and len(s) >= 8:
            ratio = len(t) / len(s)
            if ratio < 0.4 or ratio > 2.5:
                warnings.append(f"аномальная длина (x{ratio:.2f}): {k}")

    # Дубликаты: одинаковый перевод у разных ключей
    used: Dict[str, List[str]] = {}
    for k in sorted(common):
        used.setdefault(tgt[k], []).append(k)
    for v, keys in used.items():
        if len(keys) > 1 and len(v) > 3:
            warnings.append(
                f"одинаковый перевод у {len(keys)} ключей ({', '.join(keys[:5])}): {v!r}"
            )

    # Глоссарий: в источнике есть en/ru термин — в переводе должен быть tt
    if glossary:
        for row in glossary:
            tt = row.get("tt", "")
            if not tt:
                continue
            for lang in ("en", "ru"):
                term = row.get(lang, "")
                if not term:
                    continue
                for k in sorted(common):
                    if contains_term(src[k], term) and not contains_term(tgt[k], tt):
                        warnings.append(
                            f"глоссарий: в источнике «{term}», в переводе нет «{tt}»: {k}"
                        )

    return errors, warnings


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="QA татарской локализации")
    parser.add_argument("source", type=Path, help="файл-источник (JSON или .properties)")
    parser.add_argument("target", type=Path, help="файл перевода (JSON или .properties)")
    parser.add_argument("--glossary", type=Path, default=None, help="CSV-глоссарий en,ru,tt")
    parser.add_argument("--strict", action="store_true", help="считать предупреждения ошибками")
    parser.add_argument("--report", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)

    try:
        src = load_pairs(args.source)
        tgt = load_pairs(args.target)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"ошибка чтения файлов: {exc}", file=sys.stderr)
        return 1
    glossary = load_glossary(args.glossary) if args.glossary else None

    errors, warnings = check(src, tgt, glossary)

    if args.report == "json":
        print(json.dumps(
            {
                "errors": errors,
                "warnings": warnings,
                "keys_source": len(src),
                "keys_target": len(tgt),
            },
            ensure_ascii=False,
            indent=2,
        ))
    else:
        for line in errors:
            print(f"ERROR: {line}")
        for line in warnings:
            print(f"WARNING: {line}")
        if not errors and not warnings:
            print("OK: ошибок и предупреждений нет")
        print(f"итого: ошибок {len(errors)}, предупреждений {len(warnings)}")

    if errors:
        return 1
    if warnings and args.strict:
        return 1
    if warnings:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
