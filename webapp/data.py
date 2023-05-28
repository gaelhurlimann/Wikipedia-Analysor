# Incorporate data
import json

with open("./webapp/samples/all.json", "r") as f:
    DATA = json.load(f)
    PEOPLE = list(DATA.keys())
