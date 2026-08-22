# -*- coding: utf-8 -*-
"""Таблиця текстових спрайтів UI: SPRITES[motion][src][icon_id] = "текст" або dict(text=, font=, align=, upper=, pad=, fg=, bg=).
Шрифти: oswald (заголовки меню), sans (Source Sans 3 Semibold — написи налаштувань/діалогів), sans-bold, sans-reg.
Перевірено по контактних листах work/ui/<motion>/*_sheet.png."""

PILL_FG = {"dim": (88, 88, 80), "norm": (192, 192, 188), "hover": (248, 136, 0)}


def _pill(i_dim, i_norm, i_hover, i_off, text, w):
    base = {"text": text, "font": "oswald", "inset": (9, 5, w - 9, 27), "bg": (40, 40, 40), "cap_h": 20}
    return {
        i_dim: {**base, "fg": PILL_FG["dim"]},
        i_norm: {**base, "fg": PILL_FG["norm"]},
        i_hover: {**base, "fg": PILL_FG["hover"]},
        i_off: {**base, "fg": PILL_FG["dim"], "keep_red": True},
    }


def _white(text, max_w=None):
    """Білий напис без плашки з тонким темним контуром (меню: неактивні пункти). max_w — релокація з прив'язкою
    ліворуч (лівий край на місці, спрайт росте праворуч до max_w px і вниз під виносні/діакритику)."""
    d = {"text": text, "font": "oswald", "transparent": True, "rect_mesh": True, "fg": (196, 196, 190),
         "stroke": 1, "stroke_fill": (30, 30, 30, 170)}
    if max_w:
        d.update(relocate=True, anchor="left", max_w=max_w)
    return d


def _dlg(text):
    """Кнопка діалогу: білий Source Sans Semibold, мішаний регістр, тінь 2 px, капітелі 29 px (як у OK/Cancel)."""
    return {"text": text, "font": "sans", "upper": False, "transparent": True, "rect_mesh": True, "fg": (252, 252, 252),
            "cap_h": 29, "stroke": 2, "stroke_fill": (45, 45, 45, 165), "align": "center"}


def _lbl(text, max_w=780, **kw):
    """Назва опції config: білий Source Sans Semibold КАПСОМ із тонким темним контуром; релокація з прив'язкою
    ліворуч (лівий край на місці, спрайт росте праворуч до max_w)."""
    return {"text": text, "font": "sans", "upper": True, "transparent": True, "rect_mesh": True, "fg": (252, 252, 252),
            "stroke": 2, "stroke_fill": (0, 0, 0, 170), "relocate": True, "anchor": "left", "max_w": max_w, **kw}


def _val(text, fg=None, max_w=None, **kw):
    """Значення опції config (Так/Ні, У вікні, Усе…): той самий стиль, мішаний регістр. В оригіналі значення
    вирівняні ліворуч після чекбокса → з max_w релокуємо з прив'язкою ліворуч (лівий край на місці, росте
    праворуч до max_w — відстань до наступного чекбокса); без max_w — по центру старого бокса.
    fg — колір (білий / помаранчевий стан)."""
    d = {"text": text, "font": "sans", "upper": False, "transparent": True, "rect_mesh": True,
         "fg": fg or (252, 252, 252), "stroke": 2, "stroke_fill": (0, 0, 0, 170), "align": "center", **kw}
    if max_w:
        d.update(relocate=True, anchor="left", max_w=max_w)
    return d


ORANGE = (255, 138, 0)


def _mplate(text, bg=(242, 137, 0)):
    """Активний пункт меню (помаранчева смуга на темному п'єдесталі): тло задаємо явно, бо темний декор
    переважає і автовизначення бере його за тло (інвертує кольори)."""
    return {"text": text, "bg": bg}


def _cfg_guide(*texts):
    """Смуга підказок config (953×76): [гліфи] Текст × 4, білий Source Sans Semibold з м'якою тінню."""
    return {"guide": list(texts), "font": "sans", "cap_h": 22, "fg": (252, 252, 252), "stroke": 1,
            "stroke_fill": (40, 40, 40, 110), "shadows": [(1, 2, (0, 0, 0, 150))]}


def _banner(text):
    """Помаранчевий банер категорії config (шеврони по краях, антиква): текст у вікні між шевронами, банер
    розтягуємо (stretch) вставними стовпчиками, якщо напис не вміщається при капітелях 30 px."""
    return {"text": text, "font": "garamond", "upper": True, "inset": (68, 24, None, 62), "stretch": True,
            "bg": ORANGE, "fg": (40, 40, 40), "cap_h": 30, "margin": 10}


def _title(text, max_w=520):
    """Назва розділу у слоті збереження (saveload): білий Source Sans Regular, мішаний регістр, без контуру,
    прив'язка по центру → релокація по центру (полотно h 40, капітелі 22)."""
    return {"text": text, "font": "sans-reg", "upper": False, "transparent": True, "rect_mesh": True, "relocate": True,
            "cap_h": 22, "h": 40, "baseline": 30, "fg": (255, 255, 255), "align": "center", "max_w": max_w}


def _tipf(text):
    """Активний фільтр списку TIPS: помаранчевий Source Sans Bold у кружечку (прив'язка по центру → релокація
    по центру, полотно h 32, капітелі 16, не ширше кружечка 110 px)."""
    return {"text": text, "font": "sans-bold", "upper": False, "transparent": True, "rect_mesh": True, "relocate": True,
            "cap_h": 16, "h": 32, "baseline": 25, "fg": ORANGE, "align": "center", "max_w": 108, "stroke": 1,
            "stroke_fill": (0, 0, 0, 170)}


def _cell_blue(text):
    """Пункт меню телефона (синя плашка 414×47 з іконкою ліворуч): білий Source Sans. Іконка закінчується на
    x=44, EN-текст починається на x=50 — вікно від 49, інакше лишаються хвости перших літер EN; виносні EN
    сягають y=45 — низ вікна 46."""
    return {"text": text, "font": "sans", "upper": False, "inset": (49, 5, 406, 46), "bg": (43, 100, 187),
            "fg": (243, 243, 239), "cap_h": 20, "align": "left"}


def _cell_c(text, fg=None, cap_h=None, h=None):
    """Статусний напис на екрані телефона (по центру): колір задаємо явно (текст на світлому екрані),
    релокація по центру."""
    return {"text": text, "font": "sans", "upper": False, "transparent": True, "rect_mesh": True, "relocate": True,
            "cap_h": cap_h or 20, "h": h or 36, "baseline": (h or 36) - 8, "fg": fg, "align": "center"}


def _cell_l(text, max_w=300, fg=None, **kw):
    """Пункт підменю телефона (ліворуч): релокація anchor=left."""
    return {"text": text, "font": "sans", "upper": False, "transparent": True, "rect_mesh": True, "relocate": True,
            "anchor": "left", "max_w": max_w, "fg": fg, **kw}


def _chs(text):
    """Жовтий «бульбашковий» заголовок міні-гри Фейріс (charaselect): капс, товста коричнева обвідка."""
    return {"text": text, "font": "sans-black", "upper": True, "transparent": True, "rect_mesh": True,
            "relocate": True, "cap_h": 40, "h": 68, "baseline": 52, "fg": (255, 200, 15), "align": "center",
            "stroke": 4, "stroke_fill": (90, 55, 15, 255)}


CELL_DARK = (41, 41, 41)
CELL_RED = (238, 72, 56)

RETRO_TEAL = (37, 81, 97)


def _retro_item(text, max_w=460):
    """Пункт меню ретро-режиму (gamemode/command): білий капс із бірюзовим контуром; анкер ліворуч
    (originX фіксований відносно лівого краю), спрайт росте праворуч до max_w."""
    return {"text": text, "font": "sans-bold", "upper": True, "transparent": True, "rect_mesh": True,
            "fg": (255, 255, 255), "stroke": 2, "stroke_fill": RETRO_TEAL + (255,),
            "relocate": True, "anchor": "left", "max_w": max_w, "cap_h": 19}


def _retro_desc(text, max_w=550):
    """Опис пункту меню ретро-режиму: суцільний бірюзовий, мішаний регістр, анкер ліворуч."""
    return {"text": text, "font": "sans-bold", "upper": False, "transparent": True, "rect_mesh": True,
            "fg": RETRO_TEAL, "relocate": True, "anchor": "left", "max_w": max_w, "cap_h": 16}


def _retro_guide():
    """Смуга підказок ретро-режиму (світлий мармур, білий текст із чорним контуром, темні кнопки)."""
    return {"guide_light": ["Вибрати", "Підтвердити", "Назад"], "font": "sans-bold", "cap_h": 30,
            "fg": (255, 255, 255), "stroke": 3, "stroke_fill": (12, 12, 12, 255), "band": (14, 88)}


def _day(text):
    """Тег дня тижня в статусному рядку телефона (subwindow): темно-сірий блоковий капс, по центру."""
    return {"text": text, "font": "oswald-semi", "upper": True, "transparent": True, "rect_mesh": True,
            "fg": (44, 44, 44), "align": "center", "cap_h": 15}


SPRITES = {
    "title": {
        "tex#000": {
            # білі на чорній плашці
            "0019": "Список проходжень", "0021": "Налаштування", "0023": "Продовжити", "0025": "Вийти з гри",
            "0027": "Додатково", "0029": "Довідка", "0031": "Бібліотека", "0035": "Нова гра", "0037": "Спостерігач",
            "0039": "Швидке завантаження", "0068": "Нова гра",
            # помаранчеві (виділені)
            "0020": "Список проходжень", "0022": "Налаштування", "0026": "Вийти з гри", "0028": "Додатково",
            "0030": "Довідка", "0036": "Нова гра", "0038": "Спостерігач", "0040": "Швидке завантаження",
            # PRESS ANY BUTTON — антиква без кирилиці в грі; малюємо Source Sans Regular
            "0004": {"text": "Натисніть будь-яку кнопку", "font": "sans-reg", "upper": True},
        },
        "tex#001": {
            "0024": "Продовжити", "0032": "Бібліотека", "0033": "Завантажити", "0034": "Завантажити",
            "0041": "Список TIPS", "0042": "Список TIPS",
        },
    },
    "menu": {
        # 0000–0012 помаранчеві плашки (активний пункт, розмір = темному блоку п'єдесталу — не розширюємо),
        # 0013–0025 білі без плашки (звичайний стан); білі релокуємо з anchor=left: max_w = ширина плашки − ~16,
        # щоб напис не вилазив за блок п'єдесталу праворуч; висота росте під виносні (Д, У, Щ) і Й.
        # Явний bg: у спрайті плашки темний п'єдестал переважає помаранчеву смугу — автовизначення тла інвертує кольори.
        "tex#000": {
            "0004": _mplate("На весь екран"), "0005": _mplate("Довідка"), "0006": _mplate("Завантажити"),
            "0007": _mplate("Спостерігач", (255, 138, 0)), "0010": _mplate("Зберегти"),
            "0012": _mplate("Головне меню"),
            "0015": _white("Налаштування", 250), "0017": _white("На весь екран", 374), "0018": _white("Довідка", 193),
            "0019": _white("Завантажити", 172),
            "0021": _white("Швидке завантаження", 236), "0022": _white("Швидке збереження", 236), "0023": _white("Зберегти", 172),
            "0025": _white("Головне меню", 396),
        },
        "tex#001": {
            "0000": _mplate("Журнал"), "0001": _mplate("Закрити меню"), "0002": _mplate("Налаштування"),
            "0003": _mplate("Вийти з гри"), "0008": _mplate("Швидке завантаження"), "0009": _mplate("Швидке збереження"),
            "0011": _mplate("Список TIPS"), "0014": _white("Закрити меню", 369),
        },
        "tex#002": {"0013": _white("Журнал", 301), "0016": _white("Вийти з гри", 335), "0020": _white("Спостерігач", 325),
                    "0024": _white("Список TIPS", 301)},
    },
    "dialog": {
        # кнопки системних діалогів (білий Source Sans із м'якою тінню, по центру помаранчевої пілюлі 選択中):
        # EN: はい=OK, いいえ=Cancel, 確認=OK. UA: Так / Ні (YESNO_* у SYSTEM — питання «…Ви впевнені?»), 確認 лишаємо OK.
        # JP/TC/SC-варіанти не чіпаємо.
        "dialogue_img": {
            "はい_en": _dlg("Так"), "いいえ_en": _dlg("Ні"),
        },
    },
    "config": {
        # Див. docs/UI_GLOSSARY.md. Назви опцій — _lbl (капс, релокація ліворуч, max_w 780: у цьому ж слоті лежить
        # EN «STOP SKIPPING ON PHONE TRIGGER» 774 px). Значення — _val у старому боксі (центр). Пари станів:
        # білий / помаранчевий (активний). Цифри роздільностей, мови (日本語/中文), 言語設定 / Language (0120) — не чіпаємо.
        "tex#000": {
            # підписи шкал (білий Oswald-подібний дрібний капс): SLOW/MIN ліворуч, FAST/MAX праворуч
            "0002": {"text": "Швидко", "font": "oswald", "transparent": True, "rect_mesh": True, "relocate": True, "anchor": "right"},
            "0003": {"text": "Максимум", "font": "oswald", "transparent": True, "rect_mesh": True, "relocate": True, "anchor": "right"},
            "0004": {"text": "Мінімум", "font": "oswald", "transparent": True, "rect_mesh": True, "relocate": True, "anchor": "left"},
            "0008": {"text": "Повільно", "font": "oswald", "transparent": True, "rect_mesh": True, "relocate": True, "anchor": "left"},
            # кнопка DEFAULT (ПК): темна пілюля з глітч-обвідкою; сірий / помаранчевий
            "0006": {"text": "Скинути", "font": "oswald", "inset": (12, 4, 112, 28), "bg": (42, 42, 42), "cap_h": 20, "fg": (193, 193, 187),
                     "shadows": [(-1, -1, (20, 200, 196, 210)), (1, 1, (170, 30, 105, 210))]},
            "0007": {"text": "Скинути", "font": "oswald", "inset": (12, 4, 112, 28), "bg": (42, 42, 42), "cap_h": 20, "fg": ORANGE,
                     "shadows": [(-1, -1, (20, 200, 196, 210)), (1, 1, (170, 30, 105, 210))]},
            # значення ON/OFF (JP する/しない, CN 是/否 — «так/ні»)
            "0034": _val("Так", max_w=150), "0037": _val("Так", ORANGE, 150), "0030": _val("Ні", max_w=150), "0042": _val("Ні", ORANGE, 150),
            # мова: слот EN = наш переклад
            "0074": _val("Українська", max_w=155), "0075": _val("Українська", ORANGE, 155),
            # назви опцій
            "0083": _lbl("Сповіщення про TIPS"), "0095": _lbl("Роздільна здатність"),
            "0099": _lbl("Зупиняти пропуск при сигналі телефона"), "0111": _lbl("Режим екрана"),
            "0117": _lbl("Автоматичне швидке збереження"), "0143": _lbl("Затримка авторежиму"),
            "0147": _lbl("Режим пропуску"), "0153": _lbl("Швидкість тексту"),
            "0173": _lbl("Гучність музики"), "0177": _lbl("Гучність відео"), "0181": _lbl("Гучність ефектів"),
            "0185": _lbl("Гучність голосу"), "0191": _lbl("Пропускати голос"), "0195": _lbl("Синхронізація голосу"),
            # значення режиму пропуску
            "0157": _val("Усе", max_w=150), "0161": _val("Усе", ORANGE, 150), "0165": _val("Прочитане", max_w=250), "0169": _val("Прочитане", ORANGE, 250),
            # гучність голосів персонажів: імена капсом (як EN), «Female/Male Extra» — мішаний регістр
            "0199": _lbl("Інші жіночі", upper=False), "0219": _lbl("Фейріс Няннян", max_w=420), "0225": _lbl("Нае", max_w=420),
            "0241": _lbl("Маюрі", max_w=420), "0245": _lbl("Ітару", max_w=420), "0249": _lbl("Рюка", max_w=420),
            # банери категорій (заголовок сторінки, прив'язка по центру)
            "0115": _banner("Основні налаштування"), "0151": _banner("Налаштування тексту"),
            "0189": _banner("Налаштування звуку"), "0223": _banner("Налаштування голосів"),
            # смуги підказок керування (EN): Switch / PS ×3 / Xbox-ПК
            "0121": _cfg_guide("Сторінка", "Скинути", "Підтвердити", "Назад"),
            "0125": _cfg_guide("Сторінка", "Скинути", "Підтвердити", "Назад"),
            "0129": _cfg_guide("Сторінка", "Скинути", "Підтвердити", "Назад"),
            "0133": _cfg_guide("Сторінка", "Скинути", "Підтвердити", "Назад"),
            "0138": _cfg_guide("Сторінка", "Скинути", "Підтвердити", "Назад"),
        },
        "tex#001": {
            "0087": _val("У вікні", max_w=260), "0091": _val("У вікні", ORANGE, 260),
            "0103": _val("На весь екран", max_w=300), "0107": _val("На весь екран", ORANGE, 300),
            "0203": _lbl("Інші чоловічі", upper=False), "0233": _lbl("Рінтаро", max_w=420), "0257": _lbl("Судзуха", max_w=420),
        },
        "tex#002": {"0237": _lbl("Моека", max_w=420)},
        "tex#003": {"0229": _lbl("Юґо", max_w=420), "0253": _lbl("Курісу", max_w=420)},
    },
    "saveload": {
        # Логотипи SAVE / LOAD / QUICK LOAD (плати-схеми 376×1080, темні панелі) — не чіпаємо. Цифри — не чіпаємо.
        # Назви розділів (title_en, прив'язка по центру): білий Source Sans Semibold, мішаний регістр, без контуру;
        # релокуємо по центру (h 40, капітелі 22) з max_w 520. Переклад розділів — див. docs/UI_GLOSSARY.md.
        "tex#000": {
            "0102": _title("Пролог початку і кінця"), "0106": _title("Параноя подорожей у часі"),
            "0110": _title("Рандеву порожніх теорій"), "0114": _title("Дивергенція ефекту метелика"),
            "0118": _title("Гомеостаз теорії хаосу"), "0122": _title("Догма горизонту подій"),
            "0126": _title("Метафізичний некроз"), "0134": _title("Фрактальний андрогін"),
            "0142": _title("Колапс парадоксу"), "0146": _title("Небо зоряного пилу"),
            "0150": _title("Відкрити Браму Штейна"),
            # NO DATA (порожній слот): білий капс по центру; і бліда копія в заглушці мініатюри 0079
            "0076": {"text": "Немає даних", "font": "sans", "upper": True, "transparent": True, "rect_mesh": True,
                     "relocate": True, "cap_h": 27, "h": 33, "baseline": 30, "fg": (255, 255, 255), "align": "center"},
            "0079": {"text": "Немає даних", "font": "sans-bold", "inset": (64, 72, 226, 94), "bg": (44, 44, 44),
                     "fg": (92, 92, 90), "cap_h": 16},
            # PAGE над великим номером сторінки: сірий дрібний капс; росте праворуч (номер — нижче)
            "0077": {"text": "Сторінка", "font": "oswald", "transparent": True, "rect_mesh": True, "relocate": True,
                     "anchor": "left", "max_w": 170, "fg": (196, 196, 192)},
            # підписи в панелі інформації слота (помаранчеві пілюлі-контури): PLAY TIME / SAVE DATE — два вікна
            "0080": {"multi": [
                {"text": "Час гри", "font": "sans-bold", "inset": (368, 101, 496, 126), "bg": "clear", "fg": (231, 136, 30), "cap_h": 16},
                {"text": "Збережено", "font": "sans-bold", "inset": (368, 140, 496, 165), "bg": "clear", "fg": (231, 136, 30), "cap_h": 16},
            ]},
            # смуги підказок (EN): 586 px — Select / Page / Back; 831 px — Select / Page / Lock data / Back
            **{k: _cfg_guide("Вибрати", "Сторінка", "Назад") for k in ("0012", "0016", "0020", "0024", "0028")},
            **{k: _cfg_guide("Вибрати", "Сторінка", "Заблокувати", "Назад") for k in ("0055", "0059", "0063", "0067", "0071")},
        },
        "tex#001": {"0130": _title("Комплекс викривлених образів"), "0138": _title("Нескінченний апоптоз")},
    },
    "tips": {
        # Логотип TIPS LIST (0041), цифри, японський штамп 取得済み (0011) — не чіпаємо.
        "tex#000": {
            # CATEGORY (помаранчевий дрібний капс, лінія праворуч лишається) і NOTE (над описом) — вікна лише над текстом
            "0010": {"text": "Категорія", "font": "sans-bold", "inset": (8, 0, 200, 26), "bg": "clear", "fg": (255, 139, 0), "cap_h": 17, "align": "left"},
            "0017": {"text": "Опис", "font": "sans-bold", "inset": (445, 10, 535, 36), "bg": "clear", "fg": (255, 138, 0), "cap_h": 17},
            # бейдж NEW (білий капс на помаранчевій пілюлі)
            "0016": {"text": "Нове", "font": "oswald", "inset": (10, 7, 68, 29), "bg": (255, 138, 0), "fg": (255, 255, 255), "cap_h": 17},
            # фільтри (активний стан — помаранчевий, у кружечку INDEX-панелі)
            "0034": _tipf("Усі"), "0038": _tipf("Отримані"), "0043": _tipf("Нові"), "0047": _tipf("Непрочитані"),
            # INDEX-панель (EN): напис INDEX + неактивні підписи в чотирьох кружечках (темні на сірому)
            "0013": {"multi": [
                {"text": "Фільтр", "font": "sans-bold", "inset": (36, 54, 152, 86), "bg": (41, 39, 39), "fg": (198, 198, 198), "cap_h": 19},
                *[{"text": t, "font": "sans-bold", "upper": False, "inset": (cx - 50, 54, cx + 50, 84), "bg": (91, 91, 84),
                   "fg": (40, 40, 40), "cap_h": 15} for t, cx in (("Непрочитані", 200), ("Отримані", 352), ("Нові", 505), ("Усі", 657))],
            ]},
            # смуги підказок (EN): Scroll Description / Switch / Enter / Back
            **{k: _cfg_guide("Гортати опис", "Перемкнути", "Підтвердити", "Назад") for k in ("0065", "0069", "0073", "0077")},
        },
        "tex#001": {"0081": _cfg_guide("Гортати опис", "Перемкнути", "Підтвердити", "Назад")},
    },
    "cellphone": {
        # Телефон: сині пункти меню (EN-слоти), статуси (темні/червоні на світлому екрані), заголовки. Назви
        # мелодій (Easygoingness, GATE OF STEINER, Over the sky, Reunion, Precaution, Beginning of fight, Village)
        # лишаються англійськими. JP/SC/TC-варіанти не чіпаємо.
        "tex#000": {
            "0004": _cell_blue("Контакти"), "0008": _cell_blue("Повідомлення"), "0012": _cell_blue("Рингтон пошти"),
            "0016": _cell_blue("Отримати пошту"), "0020": _cell_blue("Вхідні"), "0024": _cell_blue("Змінити шпалери"),
            "0028": _cell_blue("Надіслати листа"), "0032": _cell_blue("Вихідні"), "0036": _cell_blue("Рингтон дзвінка"),
            # верхня панель (білий жирний): MAIL / No Service
            "0074": _cell_l("Пошта", 200, (255, 255, 255), upper=True, stroke=1, stroke_fill=(0, 0, 0, 120)),
            "0117": _cell_l("Немає мережі", 260, (231, 231, 231), stroke=1, stroke_fill=(0, 0, 0, 120)),
            # статуси (червоні, по центру екрана)
            "0078": _cell_c("Надіслано", CELL_RED), "0173": _cell_c("Отримано нового листа", CELL_RED),
            "0177": _cell_c("Надіслано", CELL_RED), "0185": _cell_c("Вихідний дзвінок", CELL_RED),
            "0189": _cell_c("Вхідний дзвінок", CELL_RED), "0197": _cell_c("Вам лист!", CELL_RED),
            "0205": _cell_c("Отримання", CELL_RED), "0213": _cell_c("Вам лист!", CELL_RED),
            # статуси/пункти (темні)
            "0165": _cell_c("Вимкнено", CELL_DARK), "0193": _cell_c("Немає листів", CELL_DARK),
            "0201": _cell_c("Рингтон пошти змінено", CELL_DARK), "0209": _cell_c("Шпалери змінено", CELL_DARK),
            "0217": _cell_c("Не зареєстровано", CELL_DARK), "0221": _cell_c("Рингтон змінено", CELL_DARK),
            "0229": _cell_l("Рингтон пошти", 330, CELL_DARK), "0233": _cell_l("Надсилання листа", 330, CELL_DARK),
            "0237": _cell_l("Вхідні", 330, CELL_DARK), "0241": _cell_l("Змінити шпалери", 330, CELL_DARK),
            "0245": _cell_l("Вкладення", 330, CELL_DARK), "0249": _cell_l("Застосувати", 330, CELL_DARK),
            "0253": _cell_l("Перегляд", 330, CELL_DARK), "0257": _cell_l("Відповісти", 330, CELL_DARK),
            "0261": _cell_l("Вихідні", 330, CELL_DARK), "0265": _cell_l("Подзвонити", 330, CELL_DARK),
            "0269": _cell_l("Рингтон дзвінка", 330, CELL_DARK),
            # великі сірі заголовки екранів
            "0112": _cell_l("Пошта", 414, (154, 154, 154), upper=True, font="oswald"),
            "0113": _cell_l("Меню", 414, (154, 154, 154), upper=True, font="oswald"),
            "0114": _cell_l("Налаштування", 414, (154, 154, 154), upper=True, font="oswald"),
            # помаранчеві мітки полів листа: From/Subject/To
            "0124": {"text": "Від", "font": "sans-bold", "upper": False, "inset": (2, 4, 42, 34), "bg": (255, 113, 0), "fg": (243, 242, 239), "cap_h": 16},
            "0125": {"text": "Тема", "font": "sans-bold", "upper": False, "inset": (2, 4, 42, 34), "bg": (255, 113, 0), "fg": (243, 242, 239), "cap_h": 16},
            "0126": {"text": "Кому", "font": "sans-bold", "upper": False, "inset": (2, 4, 42, 34), "bg": (255, 113, 0), "fg": (243, 242, 239), "cap_h": 16},
        },
        "tex#001": {
            "0070": _cell_l("Контакти", 200, (255, 255, 255), stroke=1, stroke_fill=(0, 0, 0, 120)),
            "0086": _cell_l("Мережа", 200, (255, 255, 255), stroke=1, stroke_fill=(0, 0, 0, 120)),
            "0098": _cell_l("Налаштування", 260, (255, 255, 255), stroke=1, stroke_fill=(0, 0, 0, 120)),
            "0082": _cell_c("Надсилання листа", CELL_RED), "0181": _cell_c("Надсилання листа", CELL_RED),
            "0090": _cell_c("Вихідний дзвінок", CELL_RED), "0094": _cell_c("Вхідний дзвінок", CELL_RED),
            "0225": _cell_l("Перегляд", 330, CELL_DARK), "0261": _cell_l("Вихідні", 330, CELL_DARK),
        },
    },
    "charaselect": {
        # міні-гра Фейріс: жовті «бульбашкові» заголовки з коричневою обвідкою (спільні для всіх мов)
        "tex#000": {
            "0008": _chs("Режим CG"), "0009": _chs("Вибір персонажа"), "0010": _chs("Режим сцен"),
            "0036": {"text": "Назад", "font": "sans-black", "upper": True, "transparent": True, "rect_mesh": True,
                     "relocate": True, "cap_h": 14, "h": 24, "baseline": 18, "fg": (255, 235, 235), "align": "center",
                     "stroke": 2, "stroke_fill": (90, 30, 30, 255)},
        },
    },
    "cgmode": {
        # галерея CG: смуги підказок (EN)
        "tex#000": {
            "0180": _cfg_guide("Змінити бібліотеку", "Сторінка", "Підтвердити", "Назад"),
            "0221": _cfg_guide("Змінити бібліотеку", "Відтворити", "Зупинити", "Змінити режим", "Назад"),
            "0224": _cfg_guide("Змінити бібліотеку", "Відтворити", "Зупинити", "Змінити режим", "Назад"),
            "0225": _cfg_guide("Змінити бібліотеку", "Відтворити", "Зупинити", "Змінити режим", "Назад"),
            "0233": _cfg_guide("Змінити бібліотеку", "Відтворити", "Зупинити", "Змінити режим", "Назад"),
            "0237": _cfg_guide("Змінити бібліотеку", "Відтворити", "Зупинити", "Змінити режим", "Назад"),
        },
        "tex#001": {
            "0184": _cfg_guide("Змінити бібліотеку", "Сторінка", "Підтвердити", "Назад"),
            "0188": _cfg_guide("Змінити бібліотеку", "Сторінка", "Підтвердити", "Назад"),
            "0192": _cfg_guide("Змінити бібліотеку", "Сторінка", "Підтвердити", "Назад"),
        },
        "tex#002": {
            "0196": _cfg_guide("Змінити бібліотеку", "Сторінка", "Підтвердити", "Назад"),
            "0200": _cfg_guide("Змінити бібліотеку", "Підтвердити", "Назад"),
            "0204": _cfg_guide("Змінити бібліотеку", "Підтвердити", "Назад"),
            "0208": _cfg_guide("Змінити бібліотеку", "Підтвердити", "Назад"),
            "0212": _cfg_guide("Змінити бібліотеку", "Підтвердити", "Назад"),
            "0216": _cfg_guide("Змінити бібліотеку", "Підтвердити", "Назад"),
        },
    },
    "cgview": {
        "tex#000": {k: _cfg_guide("Далі", "Сховати підказки", "Назад") for k in ("0000", "0004", "0008", "0012", "0016")},
    },
    "clearlist": {
        # пілюлі «Back» тут нижчі й зміщені вниз (пілюля y≈17..73, вкладка OPERATION GUIDE нижче):
        # стандартний band (5,58) обрізає гліф і бере світлі пікселі в донор — задаємо явно
        "tex#000": {"0031": {**_cfg_guide("Назад"), "band": (18, 72)}, "0047": {**_cfg_guide("Назад"), "band": (18, 72)}},
        "tex#001": {"0043": {**_cfg_guide("Назад"), "band": (18, 72)}},
    },
    "observer": {
        # смуга гайда observer має світлу окантовку зверху (y=4..5): band за замовчуванням (5,58) захоплює
        # світлий рядок → «плашки» за словами; band=(6,60) — лише темна текстура скан-ліній
        # 0138 (миша/клавіатура): 4-крапковий d-pad-гліф розріджений (fill 0.32) → нижчий поріг glyph_fill
        "tex#000": {"0138": {**_cfg_guide("Рухати курсор", "Вільне гортання", "Назад"), "band": (6, 60), "glyph_fill": 0.3}},
        "tex#001": {k: {**_cfg_guide("Рухати курсор", "Вільне гортання", "Назад"), "band": (6, 60)} for k in ("0142", "0146", "0150")},
        "tex#002": {"0154": {**_cfg_guide("Рухати курсор", "Вільне гортання", "Назад"), "band": (6, 60)}},
    },
    "help": {
        "tex#000": {k: _cfg_guide("Назад") for k in ("0029", "0032", "0033")},
    },
    # ---- ретро-режим (емуляція мобільної гри): білий текст із бірюзовим контуром, описи — бірюзові ----
    "gamemode": {
        # 0006 логотип GAMEMODE (латиниця) і 0008 (заглушка «■ メニューの内容説明文») — не чіпаємо.
        "tex": {
            "0009": _retro_item("Нова гра"), "0010": _retro_item("Завантажити"),
            "0011": _retro_item("Галерея CG"), "0012": _retro_item("Галерея сцен"),
            "0013": _retro_item("Галерея звуку"), "0014": _retro_item("Налаштування"),
            "0015": _retro_item("Довідка"), "0016": _retro_item("Вийти з гри"),
            "0017": _retro_desc("Почати гру спочатку"), "0018": _retro_desc("Продовжити гру із збереження"),
            "0019": _retro_desc("Змінити налаштування гри"), "0020": _retro_desc("Переглянути відкриті CG"),
            "0021": _retro_desc("Переглянути відкриті сцени"), "0022": _retro_desc("Прослухати відкриту музику"),
            "0023": _retro_desc("Показати довідку"), "0024": _retro_desc("Вийти з гри"),
            # смуги підказок унизу (мармур, JP): [хрестовина] 選択 [кнопка] 決定 [кнопка] 戻る
            "0003": _retro_guide(), "0004": _retro_guide(), "0005": _retro_guide(),
        },
    },
    "command": {
        # ігрове меню ретро-режиму. 0006 логотип GAMECOMMAND (латиниця), заглушки 0009 (меню-опис),
        # 0017 (プロローグ 等の章や進行度), 0020 (■ 章や目的等) — не чіпаємо.
        "tex": {
            "0010": _retro_item("Зберегти"), "0011": _retro_item("Завантажити"),
            "0012": _retro_item("Швидке збереження"), "0013": _retro_item("Швидке завантаження"),
            "0014": _retro_item("Налаштування"), "0015": _retro_item("Довідка"),
            "0016": _retro_item("Головне меню"),
            "0018": _retro_desc("Розділ 1"), "0019": _retro_desc("Розділ 2"),
            "0021": _retro_desc("Зберегти дані гри"), "0022": _retro_desc("Продовжити гру із збереження"),
            "0023": _retro_desc("Зробити швидке збереження"), "0024": _retro_desc("Зробити швидке завантаження"),
            "0025": _retro_desc("Змінити налаштування гри"), "0026": _retro_desc("Показати довідку"),
            "0027": _retro_desc("Повернутися в головне меню"),
            "0003": _retro_guide(), "0004": _retro_guide(), "0005": _retro_guide(),
        },
    },
    "button": {
        # діалог збереження ретро-режиму: заголовок セーブ + кнопки する/しない (коричневі, по центру).
        # 0019 (повзунок швидкості з мікронаписами slow/fast ~8 px) — не чіпаємо, див. REPORT.
        "tex": {
            "0020": _retro_item("Зберегти"),
            "0021": {"text": "Ні", "font": "sans-bold", "upper": False, "transparent": True, "rect_mesh": True,
                     "fg": (127, 47, 15), "align": "center", "cap_h": 16},
            "0022": {"text": "Так", "font": "sans-bold", "upper": False, "transparent": True, "rect_mesh": True,
                     "fg": (127, 47, 15), "align": "center", "cap_h": 16},
        },
    },
    "subwindow": {
        # статусний рядок телефона: теги днів тижня [MON]… (темно-сірі, дрібні). Повні назви днів не вміщаються
        # (спрайт 66–72×20, поруч цифри дати) — стандартні скорочення ПН…НД, у квадратних дужках як в оригіналі.
        # Цифри й іконки не чіпаємо.
        "tex": {
            "0015": _day("[ПТ]"), "0016": _day("[ПН]"), "0017": _day("[СБ]"), "0018": _day("[НД]"),
            "0019": _day("[ЧТ]"), "0020": _day("[ВТ]"), "0021": _day("[СР]"),
        },
    },
    "loading": {
        "tex": {
            "0001": {"text": "Завантаження...", "font": "sans-bold", "upper": False, "transparent": True,
                     "rect_mesh": True, "fg": (255, 255, 255), "stroke": 3, "stroke_fill": (14, 62, 86, 255),
                     "align": "center", "cap_h": 40},
        },
    },
    "quicksave_info": {
        # плашка QUICK SAVE (помаранчевий капс на темній панелі зі схемами); 0001 — білий «спалах», 0002 — порожня.
        "tex": {
            "0000": {"text": "Швидке збереження", "font": "oswald", "inset": (73, 27, 301, 63), "bg": "tile:303:311",
                     "fg": (229, 137, 32), "cap_h": 24},
        },
    },
    "get_tips": {
        # банер «You've received a new tip» (EN-слот 0000). 0001/0002/0003 — JP/SC/TC, не чіпаємо.
        # ~290 помаранчевих назв TIPS (EN-діапазон ≈ 0300–0590) — окреме завдання, потрібен канонічний
        # список українських назв TIPS (див. REPORT).
        # текст банера — рядки 25..46, праворуч від x≈480 крізь смугу проходить діагональна біла окантовка
        # плити → вікно до 476; тло латаємо клаптем плити нижче (bg="patch:54")
        "tex#000": {
            "0000": {"text": "Отримано новий TIPS", "font": "sans", "upper": False, "inset": (108, 22, 476, 53),
                     "bg": "patch:56", "fg": (235, 235, 235), "cap_h": 20, "align": "left"},
        },
    },
    "main": {
        "tex#000": {
            # дрібні пілюлі панелі (92×32/107×32/122×32): звичайні й помаранчеві
            # стани кожної пілюлі: 1 неактивна (сіра), 2 звичайна (світло-сіра), 3 hover/активна (помаранчева),
            # 4 недоступна (сіра + червоне перекреслення). Текст лише у вікні між бічними скобками.
            **_pill("0329", "0330", "0331", "0332", "Авто", 92),
            **_pill("0333", "0334", "0335", "0336", "Телефон", 107),
            **_pill("0337", "0338", "0339", "0340", "Пропуск", 92),
            **_pill("0341", "0342", "0343", "0344", "Система", 122),
            "0169": {"text": "Маюрі", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0173": {"text": "Фейріс", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0208": {"text": "Жінка, схоже, не шпигунка", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0212": {"text": "Жінка, що приїхала подивитись Акібу", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
        },
        "tex#001": {
            "0166": {"text": "???", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0167": {"text": "Рінтаро", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0168": {"text": "Ітару", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0170": {"text": "Курісу", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0171": {"text": "Моека", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0172": {"text": "Рюка", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0174": {"text": "Судзуха", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0175": {"text": "Махо", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0176": {"text": "Тенноджі", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0178": {"text": "Накабачі", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0179": {"text": "Батько Рюки", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0180": {"text": "Батько Фейріс", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0181": {"text": "Дворецький", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0182": {"text": "FB", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0183": {"text": "4°C", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0184": {"text": "Окабе Рінтаро через 15 років", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0185": {"text": "Ведучий", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0186": {"text": "Репортер", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0187": {"text": "Професор", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0188": {"text": "Мисливець за ракурсом А", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0189": {"text": "Мисливець за ракурсом Б", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0190": {"text": "Нападник А", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0191": {"text": "Чоловік, що вдарив Маюрі ножем", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0192": {"text": "Viral Freaks A", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0193": {"text": "Viral Freaks B", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0194": {"text": "Оголошення по станції", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0195": {"text": "Майстер", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0196": {"text": "Коментатор", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0197": {"text": "Працівник", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0198": {"text": "Сусідка", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0199": {"text": "Диктор", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0200": {"text": "Поліціянт", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0201": {"text": "Учень", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0202": {"text": "Дівчинка", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0204": {"text": "Гід", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0205": {"text": "Жінка, що знімає нишком", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0206": {"text": "Жінка, що зухвало фотографує", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0207": {"text": "Жінка, можливо, шпигунка «Організації»", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0209": {"text": "Жінка без жодної реакції", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0210": {"text": "Жінка, що ні з того ні з сього вибачилась", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0211": {"text": "Жінка, що не хоче видаляти фото", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0213": {"text": "Дивна жінка", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0214": {"text": "Покоївка", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0215": {"text": "Жінка, що назвалася Макісе", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0216": {"text": "Маюрі та Фейріс", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0217": {"text": "Курісу та Судзуха", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0218": {"text": "Рінтаро та Курісу", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0219": {"text": "Рінтаро та Моека", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0220": {"text": "Рінтаро, Маюрі та Судзуха", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
        },
        "tex#003": {
            "0177": {"text": "Нае", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
            "0203": {"text": "Черговий", "font": "garamond", "upper": False, "cap_h": 28, "relocate": True},
        },
    },
}

# Журнал (backlog): ті самі 55 плашок імен EN лежать у backlog/tex#000 як 0087..0141 (= main 0166..0220 − 79),
# без rename-map — гра вибирає їх за порядком. Копіюємо специфікації з main.
_names = {k: v for src in SPRITES["main"].values() for k, v in src.items() if "0166" <= k <= "0220"}
SPRITES["backlog"] = {"tex#000": {"%04d" % (int(k) - 79): v for k, v in _names.items()}}


def _post(text):
    """Заголовок поста @channel у журналі: помаранчевий номер (лишаємо) + нік темною антиквою (EB Garamond)."""
    return {"text": text, "font": "garamond-semi", "upper": False, "transparent": True, "rect_mesh": True,
            "keep_left": "orange", "cap_h": 20, "align": "left", "pad": 0}


# ніки дописувачів @channel (EN-спрайти 0370–0468; групи визначені порівнянням пікселів; див. UI_GLOSSARY)
_POSTS = {
    "Джон Тайтор": ["0370", "0374", "0378", "0383", "0389", "0393"],
    "Анонім": ["0371", "0373", "0376", "0377", "0379", "0380", "0381", "0382", "0386", "0387", "0388", "0390", "0399",
               "0401", "0402", "0404", "0405", "0406", "0407", "0410", "0411", "0412", "0413", "0414", "0416", "0417",
               "0425", "0428", "0431", "0434", "0437", "0438", "0439", "0440", "0441", "0454", "0455", "0456", "0458",
               "0459", "0461", "0462", "0464", "0465", "0466", "0467", "0375", "0384", "0435", "0391", "0394", "0396",
               "0400", "0420", "0421", "0422", "0426", "0432", "0445", "0447", "0448", "0449", "0450", "0451", "0460", "0395"],
    "КуріГохан та Камехамеха": ["0372", "0385", "0392", "0433", "0408", "0429", "0415", "0423", "0442", "0446"],
    "Джон Тайтор◆f8VuYnoyWU": ["0397", "0398", "0409", "0424", "0430", "0452", "0453", "0457", "0468", "0419", "0443"],
    "Темний Фенікс": ["0403", "0418", "0463", "0427", "0436", "0444"],
}
for _t, _ids in _POSTS.items():
    for _i in _ids:
        SPRITES["backlog"]["tex#000"][_i] = _post(_t)
# смуги підказок журналу (EN): Play voice / Back
for _i in ("0250", "0251", "0252", "0253", "0254"):
    SPRITES["backlog"]["tex#000"][_i] = _cfg_guide("Відтворити", "Назад")

# Кадри вибору плашки імені (main/name/chr_name_en): в оригіналі coord.y = -12/-9/-8/-13 під висоту кожного
# EN-спрайта; наші релоковані спрайти (48px, капітелі на 9..37) однакові → один y. Юра: «Рінтаро (-12) ок,
# Маюрі (-8) і Дівчинка (-9) — вище» → усім -12.
FRAME_Y = {"main": {"name_en": -12}}
