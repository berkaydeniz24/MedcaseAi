import json
from src.dialogue.dialogue_agent import DialogueAgent

def test_medcase_vaka():
    # 1. Ajanı başlat
    agent = DialogueAgent()

    # 2. Database'den gelen gerçek vaka verisi
    real_case_data = {
        "id": "PMC4528267_26306",
        "title": "61 Yaşında Female Hasta - Genel Dahiliye / Diğer Vakası",
        "specialty": "Genel Dahiliye / Diğer",
        "difficulty": "Orta",
        "narrative": "A 61-year-old obese woman presented to the plastic surgery clinic with macromastia. She underwent a Wise pattern reduction mammoplasty using an inferior pedicle without incident. On postoperative day 1, her left nipple-areolar complex (NAC) displayed venous congestion without evidence of hematoma.",
        "assets": {"images": []},
        "rubric": {
            "chief_complaint": "",
            "red_flags": [],
            "ddx_top": [],
            "tests_initial": [],
            "management_initial": [],
            "pitfalls": []
        }
    }

    # 3. Test mesajı: Öğrenci bir tedavi yöntemi öneriyor
    user_input = "Postoperatif 1. günde görülen bu venöz konjesyon (NAC congestion) için sülük tedavisi (leech therapy) uygun bir seçenek midir? Nasıl uygulanır?"

    print(f"--- Test Başlatıldı: {real_case_data['title']} ---")

    try:
        # Ajanı "hint" modunda çağırarak Sokratik yönlendirme yapmasını bekliyoruz
        response = agent.generate_response(
            user_input=user_input,
            case_data=real_case_data,
            mode="hint"
        )

        # JSON Çıktısını İnceleme
        print("\n[AJAN YANITI]")
        print(f"Cevap: {response.answer}")
        
        print("\n[TAKİP SORULARI]")
        for q in response.followups:
            print(f"- {q}")

        print("\n[META VERİ]")
        print(f"Mod: {response.meta.mode} | Branş: {response.meta.specialty}")
        
        print(f"\n[GÜVENLİK NOTU]\n{response.safety.note}")

    except Exception as e:
        print(f"Test sırasında bir hata oluştu: {e}")

if _name_ == "_main_":
    test_medcase_vaka()

