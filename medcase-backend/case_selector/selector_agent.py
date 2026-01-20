# case_selector/selector_agent.py
import json
import os
import random
from typing import Optional, Dict
from .schemas import CaseOutput, CaseRubric

class CaseSelectorAgent:
    def __init__(self):
        self.cases = []
        self.load_data()

    def load_data(self):
        # Dosya yolunu bul
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, 'data', 'cases_subset.json')
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.cases = json.load(f)
            print(f"📚 Case Selector: {len(self.cases)} vaka hafızaya alındı.")
        except Exception as e:
            print(f"❌ Veri Okuma Hatası: {e}")
            self.cases = []

    def select_random_case(self) -> Optional[Dict]:
        if not self.cases:
            return {"error": "Veri yok"}
        
        selected = random.choice(self.cases)
        return self._format_case(selected)

    def get_case_by_id(self, case_id: str) -> Optional[Dict]:
        selected = next((c for c in self.cases if c["id"] == case_id), None)
        if not selected:
            return None
        return self._format_case(selected)

    def _format_case(self, raw_data: dict) -> Dict:
        """
        Ham JSON verisini Pydantic Schema ile doğrulayıp temizler.
        """
        # --- RESİM URL MANTIĞI (GÜNCELLENDİ) ---
        image_url = None
        images = raw_data.get("assets", {}).get("images", [])
        
        if images and len(images) > 0:
            raw_img = images[0]
            
            # 1. Eğer resim verisi bir Sözlük (Dict) ise içinden dosya yolunu çıkar
            if isinstance(raw_img, dict):
                # Olası anahtarları kontrol et
                raw_img = raw_img.get("file_path") or raw_img.get("url") or raw_img.get("src")
            
            # 2. Eğer elimizde (veya işlemden sonra) bir String varsa URL yap
            if isinstance(raw_img, str):
                if raw_img.startswith("http"):
                    image_url = raw_img
                else:
                    image_url = f"http://127.0.0.1:8000/static/images/{raw_img}"

        # Rubric güvenli çekimi
        raw_rubric = raw_data.get("rubric", {})
        
        # Pydantic ile veriyi paketle
        case_obj = CaseOutput(
            id=raw_data.get("id"),
            title=raw_data.get("title", "Unknown Case"),
            specialty=raw_data.get("specialty", "General"),
            difficulty=raw_data.get("difficulty", "Intermediate"),
            narrative=raw_data.get("narrative", ""),
            image=image_url,
            rubric=CaseRubric(**raw_rubric),
            seed_questions=raw_data.get("seed_questions", [])
        )

        return case_obj.model_dump()

# Singleton Instance
selector_agent = CaseSelectorAgent()