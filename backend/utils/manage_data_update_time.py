import json


def get_now_date() -> str:
    with open("data/data_update_time.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["data_update_time"]

def update_now_date(new_date: str) -> None:
    with open("data/data_update_time.json", "w", encoding="utf-8") as f:
        json.dump({"data_update_time": new_date}, f, ensure_ascii=False, indent=4)