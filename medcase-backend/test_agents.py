# test_agents.py
import asyncio
import os
import sys
import time

# Dosya yollarını tanıtıyoruz
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from case_selector.selector_agent import selector_agent
from dialogue.dialogue_agent import DialogueAgent
from tutor.tutor_agent import tutor_agent
from tutor.schemas import TutorInput, CaseContext, UserContext

# Renkli çıktılar için
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'

async def run_stress_test():
    load_dotenv()
    print(Colors.HEADER + Colors.BOLD + "\n🚀 MEDCASE AI - DETAYLI STRES TESTİ BAŞLIYOR..." + Colors.ENDC)
    print("=" * 60)

    # 3 Farklı Vaka İçin Döngü
    for i in range(1, 4):
        print(Colors.WARNING + f"\n📢 SENARYO {i} YÜKLENİYOR..." + Colors.ENDC)
        print("-" * 30)

        # ---------------------------------------------------------
        # 1. ADIM: VAKA SEÇİMİ
        # ---------------------------------------------------------
        raw_case = selector_agent.select_random_case()
        
        if "error" in raw_case:
            print(Colors.FAIL + "❌ Kritik Hata: Vaka seçilemedi!" + Colors.ENDC)
            continue

        print(Colors.CYAN + f"📂 VAKA KİMLİĞİ: {raw_case['id']}" + Colors.ENDC)
        print(f"🏥 Branş: {raw_case['specialty']} | Zorluk: {raw_case['difficulty']}")
        print(f"📝 Başlık: {raw_case['title']}")
        print(Colors.BLUE + f"📜 Hikaye (İlk 200 karakter):\n{raw_case['narrative'][:200]}..." + Colors.ENDC)
        
        # ---------------------------------------------------------
        # 2. ADIM: DIALOGUE AGENT (İngilizce & Medikal Analiz)
        # ---------------------------------------------------------
        print("\n" + Colors.BOLD + "🤖 [DIALOGUE AGENT] Analiz Ediyor (Mode: TEACH)..." + Colors.ENDC)
        d_agent = DialogueAgent()
        
        # Zor bir soru soruyoruz
        complex_question = "Explain the pathophysiology behind the chief complaint and suggest 3 differential diagnoses."
        print(f"👤 Soru: '{complex_question}'")

        try:
            start_time = time.time()
            # 'teach' modu daha uzun cevap verir
            d_resp = d_agent.generate_response(complex_question, raw_case, mode="teach") 
            duration = time.time() - start_time
            
            print(Colors.GREEN + f"✅ Cevap Üretildi ({duration:.2f}sn):" + Colors.ENDC)
            print(Colors.CYAN + "------------------------------------------------" + Colors.ENDC)
            print(d_resp.answer.strip()) # Uzun cevabı bas
            print(Colors.CYAN + "------------------------------------------------" + Colors.ENDC)
            print(f"🔗 Takip Soruları: {d_resp.followups}")
            
        except Exception as e:
            print(Colors.FAIL + f"❌ Dialogue Hatası: {e}" + Colors.ENDC)

        # ---------------------------------------------------------
        # 3. ADIM: TUTOR AGENT (Türkçe & Eğitmen Modu)
        # ---------------------------------------------------------
        print("\n" + Colors.BOLD + "🎓 [TUTOR AGENT] Teaching (Mode: EXPLAIN)..." + Colors.ENDC)
        
        case_ctx = CaseContext(
            id=raw_case['id'],
            title=raw_case['title'],
            narrative=raw_case['narrative'],
            step=None 
        )
        
        # --- İNGİLİZCE SORU ---
        student_request = "What are the critical learning points of this case? Explain like a professor."
        print(f"👤 Student Request: '{student_request}'")

        t_input = TutorInput(
            case=case_ctx,
            user=UserContext(ask=student_request),
            mode="explain", 
            language="en" # <-- Dil İngilizce seçildi
        )

        try:
            start_time = time.time()
            t_resp = tutor_agent.run(t_input)
            duration = time.time() - start_time

            print(Colors.GREEN + f"✅ Cevap Üretildi ({duration:.2f}sn):" + Colors.ENDC)
            print(Colors.BLUE + "------------------------------------------------" + Colors.ENDC)
            print(t_resp.answer.strip()) # Uzun cevabı bas
            print(Colors.BLUE + "------------------------------------------------" + Colors.ENDC)
            
        except Exception as e:
            print(Colors.FAIL + f"❌ Tutor Hatası: {e}" + Colors.ENDC)

        print("\n" + "=" * 60)
        # API limitine takılmamak için kısa bir bekleme (Opsiyonel)
        time.sleep(2)

    print(Colors.HEADER + "🏁 STRES TESTİ TAMAMLANDI." + Colors.ENDC)

if __name__ == "__main__":
    asyncio.run(run_stress_test())