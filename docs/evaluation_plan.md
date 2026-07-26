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

### ✅ Tamamlandı — Hafta 4 (Full Experiment, 50 vaka)

`full_50` setinin tamamı (n=50) tek koşuda çalıştırıldı, sıfır hata:

| Metric | Single-Agent | Multi-Agent |
|---|---|---|
| n | 50 | 50 |
| failure_rate | 0.0 | 0.0 |
| mean_latency_ms | 2277.8 | 4801.6 |
| mean_api_calls | 1 | 3 |
| mean_total_tokens | 1483.7 | 5606.6 |
| flag: explanation_not_grounded_in_correct_option | 4 (8%) | **0 (0%)** |
| flag: low_option_distinctiveness | 0 | 1 |
| flag: possible_answer_leak_in_hint | 18 (36%) | 18 (36%) |
| flag: possible_answer_leak_in_question | **1 (2%)** | **9 (18%)** |

Ham veri: `evaluation/results/raw/full_50_n50.json`, detay: `evaluation/results/processed/full_50_n50_detail.csv`, grafikler: `evaluation/results/charts/full_50_n50_*.png`.

**Yorum (n=50 ile hâlâ tanımlayıcı istatistik, anlamlılık testi yok):**
- H4 (multi-agent daha fazla çağrı/token/gecikme kullanır) 10 vakalık pilotla tutarlı biçimde, artık 50 vaka üzerinde de doğrulandı: ~3× API çağrısı, ~3.8× token, ~2.1× gecikme.
- H1-H3 yönünde karışık bir sonuç — sadece tek taraflı bir "multi-agent kazandı" hikayesi değil, tezde tartışılmaya değer:
  - **Multi-agent lehine:** açıklamanın doğru şıkla örtüşmemesi (`explanation_not_grounded_in_correct_option`) single-agent'ta %8, multi-agent'ta **%0** — ayrı bir MCQ Agent'ın yapılandırılmış `response_schema` çıktısı, tek ajanın serbest metin üretimine göre daha tutarlı görünüyor.
  - **Single-agent lehine:** soru metninde cevabın sızması (`possible_answer_leak_in_question`) single-agent'ta %2, multi-agent'ta **%18** — multi-agent mimarisinde bu gerçek bir kalite riski, kök nedeni henüz araştırılmadı (aday hipotez: MCQ Agent'a ayrı geçirilen zengin vaka bağlamı, soruyu gereğinden fazla spesifik hale getiriyor olabilir).
  - Hint sızıntısı oranı (`possible_answer_leak_in_hint`) iki sistemde de aynı (%36) — bu flag mimariler arasında ayrım yapmıyor.

### ✅ Tamamlandı — Soru-sızıntısı kök neden analizi

`possible_answer_leak_in_question` ile flag'lenen 9 multi-agent vakası + karşılaştırma için tek flag'lenen single-agent vakası elle incelendi (`evaluation/results/raw/full_50_n50.json`).

**Bulgu:** MCQ Agent'ın (multi-agent yolu) ürettiği soru kökleri, single-agent'a göre ortalama **%56 daha uzun** (44.4 kelime vs 28.4 kelime). Flag'lenen vakalarda MCQ Agent, narrative'deki neredeyse tüm patognomonik bulguları tek soru cümlesinde art arda sıralıyor — ör. dengue vakasında soru kökü doğrudan "isles of white in a sea of red" tanımlayıcı döküntü tarifini, trombositopeni + lökopeni + Maldivler seyahat öyküsünü aynı cümlede topluyor; akromegali vakasında "growth hormone-secreting pituitary adenoma" ifadesi hem soruda hem doğru şıkta neredeyse birebir geçiyor. Aynı vaka (`PMC5292170_1230`) iki sistemde de flag'lendi — yani bazı vakalar narrative'in doğası gereği zaten sızıntıya açık, bu münferit değil.

**Kök neden (kanıt destekli hipotez):** `prompts/mcq_v1.1.txt`, rationale'ın "en az bir somut bulguya referans vermesi" gerektiğini açıkça istiyor ama soru kökü için bir uzunluk/kapsam sınırı koymuyor — MCQ Agent tüm "bütçesini" tek bir alana (soru+şıklar+rationale) ayırdığı için köke gereğinden fazla ayırt edici bulgu sığdırıyor. Single-agent modelinde aynı model aynı anda hint+explanation da üretmek zorunda olduğundan (5 alan tek yanıtta), soru kökünde muhtemelen kendiliğinden daha az detay bırakıyor. Ne `mcq_v1.1.txt` ne de `single_agent_baseline_v1.0.txt` soru kökünün cevabı sızdırmaması gerektiğini açıkça yazmıyor — sadece hint için var böyle bir kural.

### ✅ Tamamlandı — mcq_v1.2 düzeltmesi + before/after doğrulama

`prompts/mcq_v1.2.txt` eklendi (`mcq/mcq_agent.py`'nin `PROMPT_VERSION`'ı güncellendi): hint kuralına benzer açık bir kısıt eklendi — soru kökü, cevabı akıl yürütmeden belli edecek kadar çok ayırt edici bulguyu tek cümlede toplamamalı; tüm bulgular rationale'a saklanmalı. Aynı `full_50` seti (n=50, her iki sistem) yeniden çalıştırıldı; v1.1 sonucu `evaluation/results/{raw,processed,charts}/mcq_v1.1_baseline/` altında saklandı, v1.2 sonucu güncel dosyalarda.

| Metric | v1.1 Multi-Agent | v1.2 Multi-Agent |
|---|---|---|
| flag: possible_answer_leak_in_question | 9 (18%) | **7 (14%)** |
| flag: possible_answer_leak_in_hint | 18 (36%) | 14 (28%) |
| flag: explanation_not_grounded_in_correct_option | 0 | 0 |
| mean question word count | 44.4 | **54.1** |

**Dürüst sonuç — yalnızca kısmi başarı:** Sızıntı flag'i %18'den %14'e geriledi (~%22 göreli azalma), ama sıfırlanmadı. Daha ilginci, hipotezin öngördüğünün tersine, soru kökü daha da uzadı (44.4 → 54.1 kelime) — model kısıtı "daha az ayırt edici bulgu" olarak değil, "daha fazla temkinli/akıl-yürütme dili ekle" olarak yorumlamış görünüyor, ayırt edici klinik bulguları çıkarmak yerine etraflarına yorum eklemiş. **Sonuç: prompt-seviyesi düzeltme tek başına yetersiz kaldı** — bu, salt prompt mühendisliğinin sınırlarını gösteren, tezde "limitations/iterative refinement" bölümünde kullanılabilecek dürüst bir bulgu. Yapısal bir çözüm (ör. soru kökü üretildikten sonra ayrı bir "leak-check" LLM geçişi veya otomatik kontrolün flag'lediği vakalarda zorunlu repair-retry) gelecek iş olarak not edildi, bu oturumda uygulanmadı.

### ✅ Tamamlandı — Hafta 5 (Human Evaluation altyapısı: alt küme + kör form)

`evaluation/human_eval/` eklendi. Yeni LLM çağrısı yapılmadı — Hafta 4'ün `full_50_n50.json` sonucundaki (mcq_v1.2) mevcut çıktılar yeniden kullanıldı.

- **`build_blinded_set.py`** — 50 vakadan **24'lük stratified olmayan, sabit-seed (seed=7) rastgele bir alt küme** seçer (§3'te önerilen "tüm 50-100 değil, 20-30 vaka" aralığında). Her vaka için iki sistemin çıktısı **"Item 1" / "Item 2"** olarak körleniyor — hangi öğenin single/multi-agent olduğu raterlara gösterilmiyor. Etiketleme **tam dengeli** kurgulandı (12 vakada Item 1=multi-agent, 12 vakada Item 1=single-agent) — bağımsız yazı-tura yerine bilinçli dengeleme, "Item 1" pozisyonunun sistemle örtük korelasyon kurmasını mimari olarak imkansız hale getiriyor.
  - Çıktılar: `blinded_eval_set.json` (raterlara gösterilecek veri, sistem etiketi yok — repoya commit edildi) ve `unblinding_key.json` (case_id → hangi Item hangi sistem; **raterlarla paylaşılmamalı**, `.gitignore`'a eklendi).
- **`generate_form.py`** — `blinded_eval_set.json`'ı `rating_form_template.html`'e gömerek tamamen bağımsız, tek dosyalık **`rating_form.html`** üretir (harici istek/CDN yok, dosya olarak açılabilir veya bir linkle paylaşılabilir).
- **`rating_form.html`** — rater akışı: isim/rol girişi → 24 vaka, her birinde narrative + Item 1/Item 2 (soru, şıklar, doğru şık işaretli, hint, explanation) → her öğe için 5 kriter (Clinical correctness, Relevance, Consistency, Educational usefulness, Clarity), 1-5 Likert → ilerleme her adımda `localStorage`'a otomatik kaydedilir (rater yarıda bırakıp devam edebilir) → tüm vakalar bitince CSV indirme. Tarayıcıda gerçek tıklama akışıyla uçtan uca test edildi (localhost:8090 önizleme sunucusu, `.claude/launch.json`'a `human-eval-preview` config'i eklendi); ilk sürümde `<meta charset="utf-8">` eksikti ve Türkçe karakterler bozuk render oluyordu (`http.server` charset başlığı vermiyor) — düzeltildi.
- Dağıtım: `rating_form.html` 1-2 tıp öğrencisi + bir araştırma görevlisi/öğretim üyesine gönderilecek (dosya olarak ya da hafif bir statik hosting linkiyle); her rater kendi CSV'sini üretip kullanıcıya geri gönderecek.

**Bekliyor (gerçek insan verisi toplanana kadar):** Rater'lardan CSV'ler toplandıktan sonra `unblinding_key.json` ile birleştirip sistem bazında ortalama skor tablosu çıkaran bir analiz scripti (Hafta 6'nın kapsamı) henüz yazılmadı — gerçek yanıt olmadan anlamlı test edilemez.

### ⏳ Bekliyor (sıradaki haftalar, kullanıcı onayına göre)

- **Hafta 5 (devamı):** Gerçek raterlardan CSV toplama — kullanıcının `rating_form.html`'i dağıtması gerekiyor.
- **Hafta 6 — Analysis & Reporting:** Toplanan CSV'leri `unblinding_key.json` ile birleştirip sistem bazında ortalama skorlar, karşılaştırma tabloları, grafikler, hata analizi, discussion/limitations.
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
