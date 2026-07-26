# MedCase AI — Multi-Agent vs. Single-Agent Değerlendirme Planı (v1.0)

> **Kapsam:** Bu doküman, tez danışmanı geri bildiriminin 3. ve 4. maddelerine karşılık gelir:
> *"Multi-agent yaklaşımının gerçekten ne kazandırdığını deneysel olarak gösterecek bir değerlendirme planı hazırla... Uygulamanın yalnızca çalışıyor olması yeterli değil; performans, doğruluk, cevap kalitesi, kullanıcı deneyimi ve sistem mimarisi açısından da değerlendirilmesi gerekiyor."*

**Akademik iddia:** "Görevleri uzmanlaşmış ajanlara ayırmak (Case Selector, MCQ Agent, Dialogue Agent, Tutor Agent), tek bir genel amaçlı LLM ajanına kıyasla daha tutarlı ve daha güvenilir klinik eğitim çıktıları üretir." Bu iddia şu ana kadar niteliksel gözleme dayanıyordu ([architecture.md](architecture.md)); bu doküman onu **ölçülebilir** hale getirir.

---

## 1. Deney Tasarımı

Aynı klinik vakalar iki ayrı sistemde çalıştırılır:

### System A — Single-Agent Baseline
Tek bir genel amaçlı Gemini ajanı, **tek bir prompt/persona** ile şunların **hepsini** üstlenir: soru üretimi, 4 şık üretimi, doğru cevabı belirleme, hint verme, açıklama üretme. Bilinçli olarak **tek API çağrısında** çalışır (bkz. `evaluation/single_agent.py`) — bu, "uzmanlaşma" değişkenini en net şekilde izole eden tasarım: bölünmemiş tek bir persona, tüm alt görevleri aynı anda yapıyor.

### System B — Multi-Agent (mevcut mimari, değiştirilmeden)
Üretimde çalışan gerçek ajanlar **birebir**, hiç değiştirilmeden çağrılır (bkz. `evaluation/multi_agent_runner.py`):

| Adım | Ajan | Üretir |
|---|---|---|
| 1 | `MCQGenerator.generate_mcq()` | question, options[4], correct_index |
| 2 | `DialogueAgent.generate_response(mode="hint")` | hint |
| 3 | `TutorAgent.run(mode="explain")` (adım 1'deki MCQ üzerinden) | explanation |

Case Selector Agent bu deneyde ayrıca çağrılmıyor — vaka, deney çatısı (harness) tarafından **her iki sisteme de aynı şekilde** veriliyor; aksi halde ölçülen farkın mimariden mi yoksa "hangi sistem hangi vakayı gördü"den mi kaynaklandığı belirsizleşirdi.

### Kontrol edilen (sabit tutulan) değişkenler

| Değişken | Nasıl sabitlendi |
|---|---|
| Model | Her iki sistem de `.env`'deki `GEMINI_MODEL` değerini kullanıyor (şu an `gemini-3.1-flash-lite`) |
| Sıcaklık (temperature) / max token | **Hiçbiri override edilmiyor** — ne üretim ajanları (`dialogue_agent.py`, `tutor_agent.py`, `mcq_generator.py`) ne de `single_agent.py`, generation config'e temperature/max_output_tokens set etmiyor. Yani ikisi de aynı model varsayılanlarını kullanıyor. *(Not: Bu "eşitliği" sıfır-config ile sağlıyoruz — biri ayarlanıp diğeri ayarlanmazsa adil olmazdı.)* |
| Dil | Her ikisi de yalnızca İngilizce yanıt üretecek şekilde promptlanmış (mevcut `DIALOGUE_SYSTEM_PROMPT`'taki "ALWAYS respond in English" kuralına `single_agent.py`'de bilinçli olarak birebir eşlik edildi) |
| Vaka seti | `evaluation/case_sample.py` — özellik (specialty) bazında **stratified**, sabit seed (42), JSON olarak commit'lenmiş (`evaluation/case_samples/pilot_10.json`, `full_50.json`) |
| Kullanıcı soruları (hint tetikleyici) | Sabit, tek bir jenerik prompt: `"What should I consider first when evaluating this patient?"` (`multi_agent_runner.GENERIC_HINT_PROMPT`) |

### Ortak çıktı şeması

Her iki sistem de aynı şekle indirgenir (`evaluation/schemas.py`):

```python
class GeneratedContent(BaseModel):     # skorlanacak içerik
    question: str
    options: List[str]                 # tam 4
    correct_index: int                 # 0-3
    hint: str
    explanation: str

class CallMetrics(BaseModel):          # System Performance verisi
    step: str                          # "monolithic" | "mcq" | "dialogue_hint" | "tutor_explain"
    model: str
    latency_ms: float
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    success: bool
    error: Optional[str]

class SystemRunResult(BaseModel):      # bir sistemin bir vaka üzerindeki tam koşusu
    case_id: str
    system: Literal["single_agent", "multi_agent"]
    content: Optional[GeneratedContent]
    calls: List[CallMetrics]
    # + total_latency_ms, total_api_calls, total_input_tokens,
    #   total_output_tokens, failed (hesaplanan property'ler)
```

Token/latency ölçümü **üretim kodunu hiç değiştirmeden** yapılıyor: `multi_agent_runner._record()` bir context manager olarak ajanın `client.models.generate_content` metodunu geçici olarak sarmalıyor (zamanlama + `usage_metadata` yakalıyor), çağrı bitince orijinaline geri döndürüyor. Yani System B, canlı uygulamadaki halinden **bit-bir farksız**.

**Bilinen bir tuzak, tespit edilip ele alındı:** `MCQGenerator.generate_mcq()` hata durumunda exception fırlatmıyor, sabit bir fallback (`["Seçenek A", "Seçenek B", "Seçenek C", "Seçenek D"]`) döndürüyor ve hatayı yutuyor. Bu fallback'i "başarılı" saymamak için `multi_agent_runner.py` bu tam listeyle eşleşmeyi özel olarak kontrol ediyor (`_MCQ_FALLBACK_OPTIONS`).

---

## 2. Ölçülecek Boyutlar

1. **Clinical Correctness** — Doğru cevap gerçekten doğru mu? Açıklama klinik olarak güvenli mi? Uydurma bilgi var mı?
2. **Case Consistency** — Soru vaka içeriğiyle uyumlu mu? Şıklar soruyla ilgili mi? Açıklama cevabı destekliyor mu? Ajanlar arası çelişki var mı?
3. **Educational Quality** — Açıklama yalnızca cevabı mı söylüyor, yoksa akıl yürütmeyi mi açıklıyor? Yanlış şıkların neden yanlış olduğu anlatılıyor mu?
4. **MCQ Quality** — Tek/açık doğru cevap var mı? Çeldiriciler gerçekçi mi? Soru metninden cevap doğrudan tahmin edilebiliyor mu?
5. **System Performance** — Yanıt süresi, API çağrısı sayısı, token tüketimi, başarısız istek oranı, oturum tamamlanma oranı. **(Bu boyut zaten otomatik olarak `CallMetrics`/`SystemRunResult` ile toplanıyor — bkz. Bölüm 4.)**

### Puanlama (1-5)

| Kriter | Açıklama |
|---|---|
| Clinical correctness | Tıbbi doğruluk |
| Relevance | Vakayla uyumluluk |
| Consistency | Çıktılar arası tutarlılık |
| Educational usefulness | Öğreticilik |
| Clarity | Açıklık ve anlaşılabilirlik |

`OverallScore = (Correctness + Relevance + Consistency + EducationalQuality + Clarity) / 5`

Ana sonuç tablosu (doldurulacak, Hafta 4-6):

| Metric | Single-Agent | Multi-Agent |
|---|---|---|
| Clinical correctness | | |
| MCQ quality | | |
| Explanation quality | | |
| Internal consistency | | |
| Average latency | | |
| Token usage | | |
| Failure rate | | |

Multi-agent'ın **her** kriterde daha iyi çıkması şart değil — örn. daha tutarlı ama daha yavaş/maliyetli olması, mimarinin avantaj-maliyet dengesini dürüstçe gösterir; akademik olarak zayıflık değildir.

### Hipotezler

- **H1:** Multi-agent architecture produces more internally consistent clinical questions and explanations than a single-agent architecture.
- **H2:** Multi-agent architecture achieves higher educational-quality scores than the single-agent baseline.
- **H3:** Multi-agent architecture reduces clinically incorrect or unsupported responses.
- **H4:** Multi-agent architecture increases latency and API usage due to the use of multiple model calls.

**Erken pilot sinyali (2 vaka, Bölüm 5):** H4 yönünde ilk destek var — multi-agent 3 çağrı/~4.3-4.4k giriş tokenı kullanırken single-agent 1 çağrı/~1k giriş tokenı kullandı. Bu **istatistiksel bir sonuç değil**, sadece boru hattının beklenen yönde sinyal ürettiğinin kanıtı.

---

## 3. Üç Katmanlı Değerlendirme

1. **Automated Evaluation** — kodla doğrudan ölçülür, insan/LLM yargısı yok. `evaluation/automated_checks.py` şu kontrolleri üretir (`AutomatedChecks` şeması, `evaluation/schemas.py`):
   - `schema_valid`, `option_count_ok`, `has_empty_option`, `has_duplicate_options`, `correct_index_in_range` — yapısal bütünlük.
   - `explanation_grounds_correct_option` — açıklama, doğru şıkkın **ayırt edici kelime dağarcığının** (diğer 3 şıkta geçmeyen kelimeler) en az %40'ını kullanıyor mu? Kullanmıyorsa açıklama "başka bir cevabı" savunuyor olabilir.
   - `hint_leaks_correct_option` / `answer_leaked_in_question` — hint veya soru metni, doğru şıkkın ayırt edici kelime dağarcığının ≥%30'unu içeriyor mu? İçeriyorsa cevap örtük şekilde sızmış olabilir.
   - Tüm bulgular insan-okunur `flags` listesine düşer (örn. `possible_answer_leak_in_hint`).

   **Önemli sınırlama (dürüstçe belirtilmeli):** Bu kontroller kaba (coarse) sezgisel yöntemlerdir (kelime örtüşmesi), klinik/semantik anlam analizi yapmaz. "Birden fazla doğru cevap oluşması" ve "ajanlar arası çelişki" gibi tam anlamıyla semantik olan maddeler bu katmanda **yaklaşık olarak** (ayırt edicilik/sızıntı kontrolleri üzerinden) yakalanıyor, kusursuz değil — nihai karar LLM-as-a-Judge ve İnsan Uzman katmanlarına bırakılmalı.

   **Pilot doğrulama:** 3 vakalık ilk koşuda kontroller gerçek ve savunulabilir bir sinyal buldu — bir multi-agent vakasında (`PMC11052560_64735`) soru metni, doğru tanıyı ayırt eden bulguları (ör. "iris vaulting") birebir içeriyordu, yani cevap soru metninden doğrudan çıkarılabilir durumdaydı. Bu tam olarak MCQ Quality boyutundaki "Cevap, soru metninden doğrudan tahmin edilebiliyor mu?" sorusunun otomatik yakalanmasıdır — rastgele/yanlış pozitif değil.
2. **LLM-as-a-Judge** — ayrı bir değerlendirme promptuyla doğruluk/açıklık/vaka uyumu/öğreticilik/tutarlılık puanlanır. **Raporda insan değerlendirmesinin yerine geçmediği açıkça belirtilmelidir.**
3. **Human Expert Evaluation** — mümkünse 1-2 tıp öğrencisi + bir araştırma görevlisi/öğretim üyesi, çıktıların bir alt kümesini (tüm 50-100 değil, örn. 20-30 vaka) kör olarak değerlendirir (hangi çıktının hangi mimariden geldiği gizlenir).

---

## 4. Durum — Ne Şu An Hazır, Ne Bekliyor

### ✅ Tamamlandı (bu oturumda — Hafta 1 kapsamı)

| Teslim | Dosya |
|---|---|
| Ortak çıktı şeması | [`evaluation/schemas.py`](../medcase-backend/evaluation/schemas.py) |
| Single-agent baseline (System A) | [`evaluation/single_agent.py`](../medcase-backend/evaluation/single_agent.py) |
| Multi-agent instrumentation wrapper (System B) | [`evaluation/multi_agent_runner.py`](../medcase-backend/evaluation/multi_agent_runner.py) |
| Ortak, stratified, sabit-seed test vaka listesi | [`evaluation/case_sample.py`](../medcase-backend/evaluation/case_sample.py) + `evaluation/case_samples/pilot_10.json` (10 vaka), `full_50.json` (50 vaka) |
| Otomatik içerik kontrolleri (Automated Evaluation) | [`evaluation/automated_checks.py`](../medcase-backend/evaluation/automated_checks.py) — şema bütünlüğü, tekrarlı/boş şık, açıklamanın doğru şıkla örtüşmesi, hint/soruda cevap sızıntısı |
| Tam deney çatısı: JSON + detay CSV + özet CSV | [`evaluation/run_experiment.py`](../medcase-backend/evaluation/run_experiment.py) — her koşuyu otomatik kontrollerle birlikte kaydeder, sistem bazında (Single-Agent/Multi-Agent) ortalama latency/token/başarısızlık oranı + flag sayaçları üretir |

Doğrulanmış (gerçek API çağrılarıyla, varsayım değil, 3 vaka üzerinde): her iki sistem de geçerli `GeneratedContent` üretiyor; multi-agent 3 API çağrısı/~5100 token, single-agent 1 çağrı/~1470 token kullanıyor (H4 yönünde erken sinyal); otomatik kontroller en az bir vakada gerçek, savunulabilir bir MCQ kalite sorunu (cevabın soru metninden çıkarılabilir olması) yakaladı — rastgele tetiklenme değil.

### ✅ Tamamlandı — Hafta 3 (Pilot Experiment)

10 vakalık pilot setinin **tamamı** iki kez çalıştırıldı:

**İlk koşu (fix öncesi) — gerçek bir prompt/format hatası bulundu:** `multi_agent` kolunda 1/10 vaka (`PMC2810581_34430`) tamamen başarısız oldu. Kök neden loglardan izlendi: MCQ Agent'ın Gemini'den aldığı ham JSON'da `rationale` alanı hiç yoktu; eski gevşek doğrulama (`if "question" not in data or ...`) bunu değil ama yeni sıkı Pydantic doğrulaması (`mcq/schemas.py::MCQOutput`) bunu doğru şekilde reddetti — ki bu tam olarak istenen davranış, önceki gevşek koddan daha iyi. Asıl düzeltme MCQ Agent'ı **Gemini `response_schema` zorlamasına** geçirmek oldu (bkz. [architecture.md](architecture.md) §2.2) — eksik alan gibi hatalar artık yapısal olarak imkansız, bir de başarısızlık durumunda modele kendi hatası gösterilip tek bir repair denemesi yapılıyor.

**İkinci koşu (fix sonrası) — temiz sonuç:**

| Metric | Single-Agent | Multi-Agent |
|---|---|---|
| n | 10 | 10 |
| failure_rate | **0.0** | **0.0** (fix öncesi 0.1 idi) |
| mean_latency_ms | 2229.9 | 4584.8 |
| mean_api_calls | 1 | 3 |
| mean_total_tokens | 1494.3 | 5330.4 |
| flag: possible_answer_leak_in_hint | 3 | 4 |
| flag: possible_answer_leak_in_question | 0 | 2 |

Bu, hâlâ yalnızca 10 vakalık bir pilot — istatistiksel bir sonuç değil, ama H4'ü (multi-agent daha fazla çağrı/token kullanır) tutarlı biçimde destekliyor ve pipeline'ın artık hatasız çalıştığını doğruluyor. Ham veri: `evaluation/results/raw/pilot_10_n10.json`.

**Değerlendirme rubriği netleştirmesi (Hafta 3'ün diğer maddesi) henüz yapılmadı** — bu hâlâ Hafta 5-6'nın (LLM-as-a-Judge, İnsan Uzman) kapsamında.

### ⏳ Bekliyor (sıradaki haftalar, kullanıcı onayına göre)

- **Hafta 4 — Full Experiment:** 50 (veya 100) vaka üzerinde tam koşu.
- **Hafta 5 — Human Evaluation:** Kör değerlendirme için insan değerlendiricilere dağıtılacak alt küme ve form/arayüz.
- **Hafta 6 — Analysis & Reporting:** Ortalama skorlar, karşılaştırma tabloları, grafikler, hata analizi, discussion/limitations.
- **LLM-as-a-Judge promptu:** Henüz yazılmadı.

---

## 5. Nasıl Çalıştırılır

```bash
cd medcase-backend

# Ortak vaka listelerini (yeniden) üret — DB'deki Case tablosuna bağlı, seed=42
python3 -m evaluation.case_sample

# Pilot setin ilk N vakasında her iki sistemi de çalıştır (maliyeti düşük tutmak için --limit kullanın)
python3 -m evaluation.run_experiment --sample pilot_10 --limit 2
python3 -m evaluation.run_experiment --sample pilot_10                 # pilot_10'un tamamı
python3 -m evaluation.run_experiment --sample full_50 --limit 10
```

Her koşu `evaluation/results/` altına 3 dosya yazar (örn. `pilot_10_n3.json`, `pilot_10_n3_detail.csv`, `pilot_10_n3_summary.csv`):
- **`<isim>.json`** — her vaka × her sistem için tam kayıt (`SystemRunResult.to_summary_dict()` + `automated_checks`).
- **`<isim>_detail.csv`** — aynı verinin düz (flat) CSV hali, satır bazında inceleme/Excel için.
- **`<isim>_summary.csv`** — Bölüm 2'deki "Ana sonuç tablosu" formatında, Single-Agent vs Multi-Agent karşılaştırması (n, failure_rate, latency, token ortalamaları, flag sayaçları). Clinical correctness/Educational quality/Consistency satırları henüz boş — bunlar LLM-as-a-Judge ve İnsan Uzman katmanlarını (Hafta 5-6) bekliyor.
