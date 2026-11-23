# Локальные стандарты tt: число, даты, форматы

Источники: CLDR 49 (unicode-org/cldr-json, пути `main/tt/numbers.json`,
`main/tt/ca-gregorian.json`, `supplemental/plurals.json`,
`supplemental/weekData.json`); TatBLiMP (arxiv.org/pdf/2609.20832,
huggingface.co/datasets/yasalma/TatBLiMP); languagesgulper.com/eng/Tatar.html.

## Множественное число

- В CLDR для tt отдельного правила НЕТ (нет секции в plurals.json) —
  fallback на root: единственная категория `other`. Категорий one/few/many
  не существует. В i18n-библиотеках plural-формы для tt фактически не нужны —
  если фреймворк требует, объявляйте только `other`.
- Грамматика: существительное после количественного числительного стоит в
  ЕДИНСТВЕННОМ числе: «биш китап» — грамматично; «*биш китаплар» — калька с
  русского/английского (TatBLiMP, явление numeral–noun number). Аффикс
  -лар/-лер — когда множественность ничем больше не выражена.

## Числа (CLDR tt)

- Разделитель дробной части — запятая; группировка — неразрывный пробел
  (U+00A0), по 3 цифры; паттерн `#,##0.###`; пример: `12 345,67`.
- Система записи: latn.

## Даты и время (CLDR tt, григорианский)

- short: `dd.MM.y`; medium: `d MMM, y 'ел'`; long: `d MMMM, y 'ел'`;
  full: `d MMMM, y 'ел', EEEE`.
- Время: short `H:mm`; medium `H:mm:ss`; long `H:mm:ss z`; full `H:mm:ss zzzz`.
- Дни (stand-alone wide): дүшәмбе, сишәмбе, чәршәмбе, пәнҗешәмбе, җомга,
  шимбә, якшәмбе (с понедельника; weekData.firstDay.RU = mon).
- Месяцы: гыйнвар, февраль, март, апрель, май, июнь, июль, август,
  сентябрь, октябрь, ноябрь, декабрь.

## Примечания для локализации

- tt в CLDR — coverage «full», но не «modern»; в cldr-json файлы лежат по
  пути `cldr-dates-full/main/tt/...` (по одному JSON на локаль), а не
  `cldr-numbers-modern/main/tt.json`.
