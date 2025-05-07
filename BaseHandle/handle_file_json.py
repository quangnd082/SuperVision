import json
import shutil
from base_handle_file_json import HandleJSON


class HandleJsonPBA(HandleJSON):
    def add(self, name_model, config: dict):
        shutil.copytree('Model/Default', f'Model/{name_model}', dirs_exist_ok=True)
        self.save(name_model, config)

    def delete(self, name_model):
        shutil.rmtree(f'Model/{name_model}')

    def save(self, name_model, config: dict):
        with open(f'Model/{name_model}/config.json', 'w', encoding='utf-8') as file:
            json.dump(config, file, indent=4)

    def load(self, file_path='Model/Default'):
        with open(f'{file_path}/config.json', 'r', encoding='utf-8') as file:
            config = json.load(file)
            return config


if __name__ == '__main__':
    name_model_1 = 'Trung'
    name_model_2 = 'Den'
    config = {
        'trung': 1,
        'den': 555
    }
    a = HandleJsonPBA()
    a.add(name_model_1, config)
    a.add(name_model_2, config)
