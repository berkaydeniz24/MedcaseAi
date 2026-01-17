import json
import os
import random

class CaseService:
    def __init__(self):
        # Dosya yolunu bul
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.file_path = os.path.join(base_dir, 'data', 'cases_subset.json')
        self.cases = []
        self.load_data()

    def load_data(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.cases = json.load(f)
            print(f"✅ Veri seti yüklendi: {len(self.cases)} vaka.")
        except Exception as e:
            print(f"❌ Hata: {e}")
            self.cases = []

    def get_random_case(self):
        if not self.cases:
            return None
        return random.choice(self.cases)
    def get_case_by_id(self, case_id):
        # Listede ID'si eşleşen vakayı bul
        return next((c for c in self.cases if c["id"] == case_id), None)

# Tek bir instance oluşturup dışarı açıyoruz
case_service = CaseService()
