from services.case_service import case_service

class CaseSelectorAgent:
    def select_case(self):
        # Servisten vaka çek
        selected_case = case_service.get_random_case()
        
        if not selected_case:
            return {"error": "Vaka bulunamadı"}

        # --- RESİM UZANTISI DÜZELTME KISMI ---
        image_filename = selected_case.get("image_file")
        image_url = None

        if image_filename:
            # Eğer JSON'da .jpg yazıyor ama senin dosyaların .webp ise:
            if image_filename.endswith(".jpg"):
                image_filename = image_filename.replace(".jpg", ".webp")
            
            # Linki oluştur
            image_url = f"http://127.0.0.1:8000/static/images/{image_filename}"
        # -------------------------------------

        # Öğrenciye dönecek veri paketi
        return {
            "id": selected_case.get("id"),
            "narrative": selected_case.get("narrative"),
            "image": image_url, # Güncellenmiş linki gönderiyoruz
            "demographics": selected_case.get("demographics"),
            "question": selected_case.get("question"),
            "options": selected_case.get("options")
        }

case_selector_agent = CaseSelectorAgent()