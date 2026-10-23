import html
import re

import pandas as pd

STATS = []
STOPWORDS = {
    "en": set("the and of to that was for with this but his are not be by have from at they you it its who has had were her she their which what there about all one so would been will can if or when than them then into out more some".split()),
    "es": set("el la los las de que y en un una es por con para su se lo como más pero sus le al del esta este muy ya también película porque cuando sobre entre hay fue ser está tiene".split()),
    "fr": set("le la les des du et est en un une que qui dans pour pas sur au avec ce cette il elle ses mais très être sont fait comme aux ou où nous vous ils".split()),
    "de": set("der das und ist nicht ein eine mit von zu auf für er sie dem auch als wie sich sind wird nur aber oder noch bei nach aus einem einer des".split()),
    "pt": set("os um uma não que de da do em para com se é mais mas foi seu sua filme muito como são tem pelo pela também ao dos das nos nas ser está".split()),
    "it": set("il lo gli di che è per un una sono più anche del della nel nella dei delle alla questo questa molto essere hanno però".split()),
    "nl": set("het een en van dat niet met voor zijn ook maar wordt heeft naar deze nog".split()),
}
OTHER_SCRIPTS = [(0x370, 0x3FF), (0x400, 0x52F), (0x590, 0x6FF), (0x900, 0x97F), (0xE00, 0xE7F), (0x3040, 0x30FF), (0x4E00, 0x9FFF), (0xAC00, 0xD7AF)]


def read_chunks(path):
    return pd.read_json(path, lines=True, dtype=False, convert_dates=False, chunksize=10_000)


def read_columns(path, columns):
    chunks = [chunk[columns] for chunk in read_chunks(path)]
    return pd.concat(chunks) if chunks else pd.DataFrame(columns=columns)


def append_jsonl(data, file):
    for start in range(0, len(data), 10_000):
        data.iloc[start:start + 10_000].to_json(file, orient="records", lines=True, force_ascii=False)


def write_jsonl(data, path):
    with open(path, "w", encoding="utf-8") as file:
        append_jsonl(data, file)


def log(dataset, step, rows):
    STATS.append({"dataset": dataset, "step": step, "rows": rows})


def write_stats(path):
    pd.DataFrame(STATS).to_csv(path, index=False)


def words(text):
    return re.findall(r"\w+", html.unescape(text).lower())


def detect_language(text):
    sample = text[:3000]
    letters = [character for character in sample if character.isalpha()]
    other_script = sum(1 for letter in letters if ord(letter) > 0x2FF and any(low <= ord(letter) <= high for low, high in OTHER_SCRIPTS))
    if letters and other_script / len(letters) > 0.3:
        return "other"
    tokens = [token.lower() for token in re.findall(r"[^\W\d_]+", sample)][:400]
    if len(tokens) < 4:
        return "en"
    counts = {language: sum(token in stopwords for token in tokens) for language, stopwords in STOPWORDS.items()}
    language = max((language for language in counts if language != "en"), key=counts.get)
    if counts[language] > counts["en"] and counts[language] >= 2 and counts[language] / len(tokens) >= 0.12:
        return language
    return "en"


def contains_quote(article, quote):
    quote_words = words(quote)
    article_text = " " + " ".join(words(article)) + " "
    size = min(6, len(quote_words))
    return size > 0 and any(" " + " ".join(quote_words[i:i + size]) + " " in article_text for i in range(len(quote_words) - size + 1))
