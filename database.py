import json
import os

DATA_FOLDER = 'data'

def init_db():
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    archivos = ['equipos', 'ordenes', 'personal', 'repuestos', 'actividades']
    for arch in archivos:
        path = os.path.join(DATA_FOLDER, f"{arch}.json")
        if not os.path.exists(path):
            with open(path, 'w') as f:
                json.dump([], f)

def load_data(module):
    with open(os.path.join(DATA_FOLDER, f"{module}.json"), 'r') as f:
        return json.load(f)

def save_data(module, data):
    with open(os.path.join(DATA_FOLDER, f"{module}.json"), 'w') as f:
        json.dump(data, f, indent=4)

def get_next_id(module):
    data = load_data(module)
    return max([item['id'] for item in data], default=0) + 1