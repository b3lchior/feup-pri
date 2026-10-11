def write_jsonl(data, path):
    with open(path, "w", encoding="utf-8") as file:
        for start in range(0, len(data), 100_000):
            data.iloc[start:start + 100_000].to_json(file, orient="records", lines=True, force_ascii=False)
