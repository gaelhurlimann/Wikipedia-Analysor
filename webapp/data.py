# Incorporate data
import json

with open("./webapp/samples/results.json", "r", encoding='utf8') as f:
    DATA = json.load(f)
    PEOPLE = list(DATA.keys())
