import json

class DataLoader:
    @staticmethod
    def load_json(file_path):

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"Hata: {file_path} bulunamadı!")
            return None

    @staticmethod
    def get_stops(data):

        if not data:
            return []
        return data.get("duraklar", [])

    @staticmethod
    def get_taxi_info(data):

        if not data:
            return {}
        return data.get("taxi", {})
