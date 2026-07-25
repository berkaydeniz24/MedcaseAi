# MedCase AI

Tıp öğrencileri için, gerçek PubMed Central vaka raporlarından üretilen klinik vakalar üzerinde Sokratik yöntemle çalışan, çoklu-ajan (multi-agent) bir eğitim uygulaması. FastAPI + SQLite backend, Expo/React Native frontend, Google Gemini destekli.

Bu proje bir bitirme (lisans/lisansüstü) tezi kapsamında geliştirilmektedir; akademik danışman geri bildirimi doğrultusunda hem uygulama hem de deneysel değerlendirme altyapısı adım adım inşa edilmektedir.

---

## İçindekiler

- [Mimari](#mimari)
- [Veri Kümesi](#veri-kümesi)
- [Kurulum](#kurulum)
- [Backend](#backend)
- [Frontend](#frontend)
- [API](#api)
- [Değerlendirme (Evaluation)](#değerlendirme-evaluation)
- [Yol Haritası](#yol-haritası)
- [Ekran Görüntüleri](#ekran-görüntüleri)
- [Gelecek Çalışmalar](#gelecek-çalışmalar)

---

## Mimari

MedCase AI, tek bir genel amaçlı ajan yerine **rol-uzmanlaşmış, sabit topolojili bir çoklu-ajan boru hattı** olarak tasarlanmıştır:

| Ajan | Konum | Görev | LLM? |
|---|---|---|---|
| **Case Selector Agent** | `medcase-backend/case_selector/` | SQLite `cases` tablosundan vaka seçimi/getirme, şema doğrulama | Hayır (deterministic) |
| **MCQ Agent** | `medcase-backend/mcq/` | Vaka anlatısından 4 şıklı soru üretimi | Evet (Gemini) |
| **Dialogue Agent** | `medcase-backend/dialogue/` | Sokratik yöntemle yönlendirici diyalog (hint/explain/teach modları) | Evet (Gemini) |
| **Tutor Agent** | `medcase-backend/tutor/` | MCQ cevabı sonrası pedagojik geri bildirim | Evet (Gemini) |

Ajanlar birbirini doğrudan çağırmaz; koordinasyonu FastAPI router katmanı (`routers/dialogue_router.py`) üstlenir. Ortak altyapı: `services/gemini_client.py` (tek paylaşımlı Gemini istemcisi), `services/prompt_loader.py` + `prompts/*.txt` (versiyonlanmış promptlar), `services/logging_config.py` (INFO/WARNING/ERROR ayrı log dosyaları).

Tüm ajanların görev tanımı, prompt yapısı, girdi/çıktı şemaları ve ajanlar arası iletişim protokolü için: **[docs/architecture.md](docs/architecture.md)**.

## Veri Kümesi

200 vakalık alt küme (`medcase-backend/data/cases_subset.json`), [MultiCaRe Dataset](https://github.com/mauro-nievoff/MultiCaRe_Dataset)'ten (PubMed Central açık erişim vaka raporları) türetilmiştir. Sekiz branş: Gastroenterology, Dermatology, Neurology, Orthopedics & Traumatology, Cardiology, Ophthalmology, Pulmonology, General Internal Medicine.

**Lisans durumu** (200 vakanın tamamı NCBI Open Access servisine tek tek sorgulanarak doğrulandı): %64,5 CC BY, %21,5 CC BY-NC, %14 CC BY-NC-SA — yani vakaların %35,5'i yalnızca ticari olmayan kullanıma izin veriyor. Detaylı döküm, metodoloji ve ham veri: **[docs/dataset.md](docs/dataset.md)** + [docs/dataset_license_audit.json](docs/dataset_license_audit.json).

## Kurulum

Gereksinimler: Python 3.12+, Node.js 22+, bir Google Gemini API anahtarı ([aistudio.google.com](https://aistudio.google.com/apikey)).

```bash
git clone <bu repo>
cd MedcaseAI
```

### Backend

```bash
cd medcase-backend
pip install -r ../requirements.txt

# .env dosyası oluştur
cat > .env <<EOF
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.1-flash-lite
EOF

python3 main.py
# -> http://127.0.0.1:8000  (ilk açılışta cases_subset.json otomatik SQLite'a yüklenir)
```

### Frontend

```bash
cd medcase-frontend
npm install

cat > .env <<EOF
EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
EOF

npx expo start        # veya --ios / --android / --web
```

## Backend

- **Framework:** FastAPI + Uvicorn
- **Veritabanı:** SQLite (SQLAlchemy) — `cases`, `chat_sessions`, `chat_messages`, `user_stats`, `case_progress` tabloları. Tüm oturum/cevap/geçmiş verisi SQL'de tutulur (RAM tabanlı fallback yoktur).
- **LLM:** Google Gemini (`google-genai` SDK), model adı `.env`'deki `GEMINI_MODEL` ile kontrol edilir — güncel çalışan modeller için [docs/architecture.md](docs/architecture.md)'deki notlara bakın (birçok eski model adı, ör. `gemini-1.5-flash`, artık API'den kaldırılmış durumda).
- **Loglama:** `medcase-backend/logs/{info,warning,error}.log` + konsol.
- **Promptlar:** `medcase-backend/prompts/*_v1.0.txt`, `services/prompt_loader.py` ile yüklenir; her ajan çağrısında kullanılan prompt versiyonu loglanır.

## Frontend

Expo Router tabanlı React Native uygulaması (`medcase-frontend/`): ana sayfa, vaka kütüphanesi (branş filtreli), vaka detay + MCQ, sohbet (hint/explain/teach modları arası geçiş), geçmiş, istatistikler, profil.

## API

| Endpoint | Açıklama |
|---|---|
| `GET /cases` | Tüm vakaların özet listesi (SQL) |
| `GET /cases/{case_id}` | Tek vaka detayı |
| `GET /dialogue/start` | Rastgele vaka seç + MCQ üret + oturum başlat |
| `POST /dialogue/{case_id}/chat` | Sokratik diyalog turu (mode: hint/explain/teach) |
| `POST /dialogue/{session_id}/answer` | MCQ cevabını değerlendir + Tutor Agent geri bildirimi |
| `GET /dialogue/history/{session_id}` | Oturum mesaj geçmişi |
| `GET /user/stats`, `/user/progress`, `/user/history` | Kullanıcı istatistikleri |

Tam istek/yanıt şemaları için `medcase-backend/routers/` altındaki Pydantic modellerine bakın.

## Değerlendirme (Evaluation)

Projenin akademik iddiası — *"görevleri uzmanlaşmış ajanlara ayırmak tek bir genel amaçlı ajana kıyasla daha tutarlı/güvenilir çıktı üretir"* — `medcase-backend/evaluation/` altında deneysel olarak test ediliyor:

- **System A (single-agent baseline)** vs **System B (mevcut, değiştirilmemiş multi-agent mimari)** karşılaştırması
- Ortak, stratified, sabit-seed test vaka listesi (`evaluation/case_samples/`)
- Otomatik içerik kontrolleri: şema bütünlüğü, tekrarlı/boş şık, cevabın soru/hint metninden sızması (`evaluation/automated_checks.py`)
- Latency/token/API-çağrısı ölçümü, üretim kodunu değiştirmeden (`evaluation/multi_agent_runner.py`)
- JSON + CSV + karşılaştırma grafikleri (`evaluation/run_experiment.py`, `evaluation/charts.py`)

```bash
cd medcase-backend
python3 -m evaluation.run_experiment --sample pilot_10 --limit 2
```

Hipotezler (H1-H4), ölçüm boyutları, puanlama rubriği ve haftalık plan için: **[docs/evaluation_plan.md](docs/evaluation_plan.md)**.

## Yol Haritası

Tez danışmanı geri bildirimine dayalı, adım adım ilerleyen bir yol haritası izleniyor:

1. ✅ Sistem mimarisi (ajan envanteri, prompt yapıları, I/O şemaları, iletişim protokolü) — [docs/architecture.md](docs/architecture.md)
2. ✅ Veri kümesi incelemesi (yapı, lisans denetimi, kullanım) — [docs/dataset.md](docs/dataset.md)
3. 🔄 Multi-agent vs single-agent deneysel karşılaştırma planı — [docs/evaluation_plan.md](docs/evaluation_plan.md) (Hafta 1-2 tamamlandı: ortak şema, single-agent baseline, otomatik metrikler; Hafta 3-6 devam ediyor)
4. ⏳ Çok boyutlu değerlendirme (performans, doğruluk, cevap kalitesi, UX, mimari)
5. ⏳ Haftalık hedefler ve düzenli ilerleme takibi

## Ekran Görüntüleri

_Eklenecek — vaka kütüphanesi, sohbet ekranı ve rapor görünümünden ekran görüntüleri buraya konulacak._

## Gelecek Çalışmalar

- Clinical Reasoning Score (History / Differential Diagnosis / Labs / Treatment alt puanları)
- Kullanıcı kimlik doğrulama (SQLite tabanlı basit kullanıcı sistemi)
- Standartlaştırılmış API yanıt zarfı (`{success, data, error}`)
- `tests/` altında agent/DB/API için otomatik testler (LLM çağrıları mock'lanarak)
- Açık `Agent Manager` / orkestratör bileşeni (şu an koordinasyon router katmanında örtük)
- Görüntü tabanlı vakalar (X-ray/CT/MRI) ve sesli etkileşim
- Veri kümesini MultiCaRe'den kademeli büyütme (200 → 300 → 1000 vaka)
