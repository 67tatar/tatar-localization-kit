"""Тесты qa_strings.py: механика проверок на синтетических парах файлов."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import qa_strings  # noqa: E402


def write_json(tmp: tempfile.TemporaryDirectory, name: str, data: dict) -> Path:
    path = Path(tmp.name) / name
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


class QaStringsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_key_is_error(self):
        src = write_json(self.tmp, "src.json", {"save": "Сохранить", "open": "Открыть"})
        tgt = write_json(self.tmp, "tgt.json", {"save": "Сакларга"})
        errors, _ = qa_strings.check(qa_strings.load_pairs(src), qa_strings.load_pairs(tgt))
        self.assertTrue(any("нет ключа в переводе: open" in e for e in errors))

    def test_extra_key_is_error(self):
        src = write_json(self.tmp, "src.json", {"save": "Сохранить"})
        tgt = write_json(self.tmp, "tgt.json", {"save": "Сакларга", "foo": "Бар"})
        errors, _ = qa_strings.check(qa_strings.load_pairs(src), qa_strings.load_pairs(tgt))
        self.assertTrue(any("лишний ключ в переводе: foo" in e for e in errors))

    def test_placeholder_lost_is_error(self):
        src = write_json(self.tmp, "src.json", {"greet": "Привет, {name}!"})
        tgt = write_json(self.tmp, "tgt.json", {"greet": "Сәлам!"})
        errors, _ = qa_strings.check(qa_strings.load_pairs(src), qa_strings.load_pairs(tgt))
        self.assertTrue(any("плейсхолдеры не совпадают" in e for e in errors))

    def test_placeholder_intact_is_ok(self):
        src = write_json(self.tmp, "src.json", {"greet": "Привет, {name}!", "n": "%d файлов"})
        tgt = write_json(self.tmp, "tgt.json", {"greet": "Сәлам, {name}!", "n": "%d файл"})
        errors, _ = qa_strings.check(qa_strings.load_pairs(src), qa_strings.load_pairs(tgt))
        self.assertFalse(any("плейсхолдеры" in e for e in errors))

    def test_untranslated_is_warning(self):
        src = write_json(self.tmp, "src.json", {"save": "Сохранить изменения"})
        tgt = write_json(self.tmp, "tgt.json", {"save": "Сохранить изменения"})
        _, warnings = qa_strings.check(qa_strings.load_pairs(src), qa_strings.load_pairs(tgt))
        self.assertTrue(any("не переведено" in w for w in warnings))

    def test_trailing_space_is_error(self):
        src = write_json(self.tmp, "src.json", {"ok": "OK"})
        tgt = write_json(self.tmp, "tgt.json", {"ok": "Яхшы "})
        errors, _ = qa_strings.check(qa_strings.load_pairs(src), qa_strings.load_pairs(tgt))
        self.assertTrue(any("пробелы по краям" in e for e in errors))

    def test_empty_translation_is_error(self):
        src = write_json(self.tmp, "src.json", {"save": "Сохранить"})
        tgt = write_json(self.tmp, "tgt.json", {"save": ""})
        errors, _ = qa_strings.check(qa_strings.load_pairs(src), qa_strings.load_pairs(tgt))
        self.assertTrue(any("пустой перевод" in e for e in errors))

    def test_nested_json_flattens(self):
        src = write_json(self.tmp, "src.json", {"menu": {"file": "Файл"}})
        pairs = qa_strings.load_pairs(src)
        self.assertEqual(pairs, {"menu.file": "Файл"})

    def test_properties_format(self):
        path = Path(self.tmp.name) / "tt.properties"
        path.write_text("# комментарий\nsave=\u0421\u0430\u043a\u043b\u0430\u0440\u0433\u0430\n", encoding="utf-8")
        pairs = qa_strings.load_pairs(path)
        self.assertEqual(pairs, {"save": "Сакларга"})

    def test_glossary_violation_is_warning(self):
        src = write_json(self.tmp, "src.json", {"btn": "Сохранить файл"})
        tgt = write_json(self.tmp, "tgt.json", {"btn": "Файлны саклау"})
        glossary = [{"en": "save", "ru": "Сохранить", "tt": "саклау"}]
        _, warnings = qa_strings.check(qa_strings.load_pairs(src), qa_strings.load_pairs(tgt), glossary)
        # «саклау» есть в переводе — нарушения быть не должно
        self.assertFalse(any("глоссарий" in w for w in warnings))
        glossary_bad = [{"en": "file", "ru": "файл", "tt": "документ"}]
        _, warnings = qa_strings.check(qa_strings.load_pairs(src), qa_strings.load_pairs(tgt), glossary_bad)
        # «документ» отсутствует в переводе при «файл» в источнике — предупреждение
        self.assertTrue(any("глоссарий" in w for w in warnings))

    def test_contains_term_word_boundary(self):
        self.assertTrue(qa_strings.contains_term("Сохранить файл", "файл"))
        self.assertFalse(qa_strings.contains_term("Сохранить файлы", "файл"))
        self.assertTrue(qa_strings.contains_term("Save file now", "file"))

    def test_main_exit_codes(self):
        src = write_json(self.tmp, "src.json", {"save": "Сохранить"})
        tgt_ok = write_json(self.tmp, "ok.json", {"save": "Сакларга"})
        tgt_warn = write_json(self.tmp, "warn.json", {"save": "Сохранить"})
        self.assertEqual(qa_strings.main([str(src), str(tgt_ok)]), 0)
        self.assertEqual(qa_strings.main([str(src), str(tgt_warn)]), 2)
        self.assertEqual(qa_strings.main([str(src), str(tgt_warn), "--strict"]), 1)


if __name__ == "__main__":
    unittest.main()
