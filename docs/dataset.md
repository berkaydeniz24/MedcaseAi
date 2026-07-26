# MedCase AI — Veri Kümesi İncelemesi (v1.0)

> **Kapsam:** Bu doküman, tez danışmanı geri bildiriminin 2. maddesine karşılık gelir:
> *"Kullanacağın veri kümesini ayrıntılı şekilde incele. Veri yapısını, lisans durumunu ve projede nasıl kullanılacağını netleştir."*
>
> Aşağıdaki bulgular varsayım değil, **doğrulanmış ölçümdür**: `medcase-backend/data/cases_subset.json`'daki 200 vakanın **tamamı** NCBI'nin resmi Open Access web servisine (`oa.fcgi`) tek tek sorgulanarak lisans bilgisi tarafımca canlı olarak çekildi (2026-07-26). Yöntem Bölüm 4'te tarif edilmiştir, tekrarlanabilir.

---

## 1. Veri Kümesinin Kökeni

Kullanıcı tarafından paylaşılan referans: **[MultiCaRe Dataset](https://github.com/mauro-nievoff/MultiCaRe_Dataset)** (Nievas Offidani et al.).

- **Ne olduğu:** PubMed Central (PMC) açık erişim alt kümesindeki **72.000+ vaka raporu makalesinden** çıkarılmış, kimlik bilgileri temizlenmiş **98.000+ klinik vaka** ve bunlara eşlik eden **139.000+ tıbbi görüntü** içeren, akademik olarak yayımlanmış (Nievas Offidani, M. et al., *Data*, 10(8), 123, 2025) ve Zenodo'da barındırılan (DOI: `10.5281/zenodo.10079369`) büyük ölçekli bir kaynak.
- **Nasıl üretildiği:** PMC makaleleri BioPython ile sorgulanıp (`1_How_to_Query_Case_Reports...ipynb`), metin+görsel çıkarılıyor (`2_Data_Extraction...ipynb`), görseller ön işleniyor (`3_Image_Preprocessing...ipynb`) ve görsel altyazıları 140+ sınıflık bir taksonomiye göre otomatik etiketleniyor (`4_Turning_Captions_into_Image_Labels...ipynb`).
- **Erişim yöntemi:** `pip install multiversity` paketi ile filtrelenmiş alt küme (subset) üretimi destekleniyor; ham veri Zenodo'dan indirilebiliyor.

**Önemli tespit — kimlik (ID) doğrulaması:** MultiCaRe dokümantasyonu, her hastaya bir `patient_id` verildiğini ve bunun *"makalenin PMC'si + sıralı bir numara birleştirilerek"* oluşturulduğunu belirtiyor. Bizim `cases_subset.json`'daki ID formatı da birebir bu şablona uyuyor: **`PMC{makale_no}_{sıra_no}`** (ör. `PMC4528267_26306`). Bu, projedeki 200 vakalık alt kümenin **MultiCaRe'den türetildiğini** (veya MultiCaRe ile aynı üretim hattından/aynı ID şemasıyla üretildiğini) doğruluyor.

---

## 2. Şema Karşılaştırması: MultiCaRe (tam) vs. `cases_subset.json` (bizim alt kümemiz)

| Alan | MultiCaRe'de var mı? | `cases_subset.json`'da var mı? | Not |
|---|---|---|---|
| `patient_id` / `id` | ✅ | ✅ | Format birebir uyuşuyor |
| `age`, `gender` | ✅ | ❌ | Hasta demografisi alt kümede yok |
| `case_strings` (klinik anahtar kelimeler) | ✅ | ❌ kısmen → `narrative` içine gömülü serbest metin olarak var | Yapılandırılmış alan yok |
| `keywords`, `mesh_terms` | ✅ | ❌ | Yok |
| `license` (makale bazlı) | ✅ | ❌ | **Kritik eksik — Bölüm 3'e bakınız** |
| `citation` | ✅ (dolaylı, `oa.fcgi` üzerinden türetilebilir) | ❌ | Atıf/kaynak gösterimi için gerekli, yok |
| `specialty` | Kısmen (etiket/label bazlı) | ✅ (8 branş, doğrudan alan) | MedcaseAI'ye özgü, muhtemelen üretim sırasında türetilmiş |
| `difficulty` | ❌ (MultiCaRe'de yok) | ✅ ama **200/200 vaka "Intermediate"** | MedcaseAI'ye özgü alan; şu an ayırt edici değil (bkz. Bölüm 5.3) |
| `rubric` (chief_complaint, red_flags, ddx_top, tests_initial, management_initial, pitfalls) | ❌ (MultiCaRe'de yok) | ✅ şema var ama **200/200 vaka tamamen boş** | MedcaseAI'ye özgü, planlanmış ama **hiç doldurulmamış** bir zenginleştirme adımı |
| `seed_questions` | ❌ (MultiCaRe'de yok) | ✅ şema var ama **200/200 vaka boş liste** | Aynı şekilde, planlanmış ama boş |
| `assets.images[].file/caption/modality` | ✅ (`file`, `caption`, `label`) | ✅ (162/200 vakada en az 1 görsel) | Alan adı `label`→`modality` olarak yeniden adlandırılmış görünüyor |

**Sonuç:** `cases_subset.json`, MultiCaRe'nin **çok küçük ve budanmış** bir görünümü. Özellikle **`license` ve `citation` alanlarının hiç taşınmamış olması**, aşağıdaki lisans analizinin *neden yeniden, dıştan (NCBI'den) hesaplanması gerektiğini* açıklıyor — bu bilgi dosyanın içinde zaten yoktu.

`rubric` ve `seed_questions`, MultiCaRe'nin bir parçası değil; bunlar **MedcaseAI'ye özgü, planlanmış ama henüz uygulanmamış bir LLM-destekli vaka zenginleştirme adımının** boş kalıpları (muhtemelen ileride bir "Rubric Generator" ajanıyla doldurulması planlanmıştı — mimari dokümanındaki [architecture.md](architecture.md) Bölüm 6, madde 1 ile aynı bulgu).

---

## 3. Lisans Durumu — Ölçülmüş Sonuçlar

### 3.1 İki farklı lisans katmanı var, karıştırılmamalı

1. **Derleme/kod lisansı (MultiCaRe repo & Zenodo kaydı): CC0 1.0 Universal.** Bu, MultiCaRe'nin *derleme mantığı, kod, taksonomi* için geçerli — "tüm hakların feragat edildiği", atıf gerektirmeyen bir kamu malı bildirimi.
2. **Kaynak makale lisansı (her PMC makalesinin kendi lisansı): DEĞİŞKEN.** MultiCaRe'nin kendi dokümantasyonu bunu açıkça ayırıyor ve filtrelenebilir bir `license` alanı sunuyor; olası değerler: `CC0, CC BY, CC BY-SA, CC BY-ND` (ticari kullanıma izin veren), `CC BY-NC, CC BY-NC-SA, CC BY-NC-ND` (yalnızca ticari olmayan kullanım) ve `author_manuscript` / `NO-CC CODE` (en kısıtlayıcı, açık lisans yok).

**"MultiCaRe CC0'dır" demek yanıltıcı olur** — CC0 yalnızca derlemenin/veri setinin *paketleme* hakkına ilişkindir; vaka metninin kendisi (narrative) hâlâ orijinal makalenin telif sahibine ait ve o makalenin kendi CC lisansına tabidir.

### 3.2 Bizim 200 vakalık alt kümemizin gerçek lisans dağılımı (200/200 doğrulandı)

`cases_subset.json`'daki 200 vakanın PMC kimlikleri tek tek NCBI'nin resmi Open Access servisine (`https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMC...`) sorgulanarak elde edildi:

| Lisans | Vaka sayısı | Oran | Anlamı |
|---|---|---|---|
| **CC BY** | 129 | %64,5 | Ticari kullanım dahil serbest, **atıf zorunlu** |
| **CC BY-NC** | 43 | %21,5 | **Ticari kullanım YASAK**, atıf zorunlu |
| **CC BY-NC-SA** | 28 | %14,0 | **Ticari kullanım YASAK**, atıf zorunlu, türev eserler aynı lisansla paylaşılmalı (ShareAlike) |
| CC0 / CC BY-ND / author_manuscript / NO-CC CODE | 0 | %0 | Bu alt kümede rastlanmadı |

**➡️ Toplamda 200 vakanın 71'i (%35,5'i) yalnızca ticari olmayan kullanıma izin veriyor (CC BY-NC + CC BY-NC-SA).**

Branşa göre kırılım:

| Branş | CC BY | CC BY-NC | CC BY-NC-SA | Toplam |
|---|---|---|---|---|
| Cardiology | 15 | 2 | 3 | 20 |
| Dermatology | 28 | 5 | 3 | 36 |
| Gastroenterology | 22 | 12 | 7 | 41 |
| General Internal Medicine / Other | 3 | 2 | 1 | 6 |
| Neurology | 19 | 6 | 10 | 35 |
| Ophthalmology | 11 | 8 | 1 | 20 |
| Orthopedics & Traumatology | 19 | 3 | 3 | 25 |
| Pulmonology | 12 | 5 | 0 | 17 |

*(Gastroenterology ve Neurology, NC/NC-SA oranı en yüksek branşlar — özellikle bu branşlarda ticari kullanım riski daha yoğun.)*

### 3.3 MedcaseAI için pratik anlamı

- **Mevcut kullanım (bitirme tezi, eğitim amaçlı, ücretsiz, akademik demo):** Düşük risk. Hem CC BY hem CC BY-NC/NC-SA, eğitim/akademik amaçlı, ticari olmayan kullanıma izin verir. Ancak **atıf zorunluluğu tüm 200 vaka için geçerli** (CC BY de dahil — "serbest" olan bile atıfsız kullanılamaz).
- **Şu an eksik olan:** Uygulama, bir vakanın hikâyesini (`narrative`) kullanıcıya gösterirken **hiçbir kaynak/atıf bilgisi göstermiyor** (bkz. `medcase-frontend/app/case/[id]/chat.js` — "Clinical File" modalı yalnızca ham `narrative` metnini basıyor). Bu, CC BY'nin bile gerektirdiği asgari atıf (yazar, başlık, kaynak, lisans, değişiklik notu) yükümlülüğünü karşılamıyor.
- **Gelecekte ticarileştirme / App Store yayını / geniş kamuya açık dağıtım düşünülürse:** 71 vaka (%35,5) CC BY-NC/NC-SA nedeniyle **doğrudan engel teşkil eder** — ya bu 71 vaka ürün dışında tutulmalı ya da yalnızca ticari olmayan bir sürümde kullanılmalıdır.
- **Yeniden üretilebilirlik notu:** Depoda, `cases_subset.json`'ın MultiCaRe'den hangi filtrelerle (`multiversity` parametreleri) türetildiğini gösteren bir betik **yok** — yalnızca sonuç dosyası commit'lenmiş. Bu, veri kümesinin nasıl seçildiğinin (neden bu 200 vaka / bu 8 branş) tezde "yeniden üretilebilirlik" açısından bir soru işareti bırakıyor; en azından tezde "alt küme elle/harici olarak MultiCaRe'den seçilmiştir, seçim kriterleri belirtilmemiştir" şeklinde dürüstçe belirtilmesi önerilir.

---

## 4. Yöntem (Tekrarlanabilirlik İçin)

```bash
# 1) cases_subset.json'daki 200 vakanın PMC kimliklerini çıkar
python3 -c "
import json
with open('medcase-backend/data/cases_subset.json', encoding='utf-8') as f:
    data = json.load(f)
ids = sorted(set(c['id'].split('_')[0] for c in data))
print('\n'.join(ids))
" > pmc_ids.txt

# 2) Her biri için NCBI Open Access servisini sorgula (resmi, ücretsiz, kimlik doğrulama gerektirmiyor)
cat pmc_ids.txt | xargs -P 6 -I {} bash -c \
  'curl -s --max-time 15 "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={}" > oa_responses/{}.xml'

# 3) license="..." alanını regex ile çıkar ve say
```

200/200 sorgu başarıyla yanıtlandı (hata/kayıp kayıt yok). Ham sonuç (200 vakanın tamamı için `case_id`, `pmcid`, `specialty`, `license`, `citation`) [dataset_license_audit.json](dataset_license_audit.json) dosyasında saklanıyor — tez ekinde kanıt/appendix olarak doğrudan kullanılabilir.

---

## 5. Diğer Veri Kalitesi Gözlemleri (Lisans Dışı)

1. **`rubric` alanları 200/200 vakada tamamen boş.** Şema (`chief_complaint`, `red_flags`, `ddx_top`, `tests_initial`, `management_initial`, `pitfalls`) mevcut ama içerik hiç üretilmemiş. Dialogue/Tutor Agent promptları bu alanlara referans verebilecek şekilde tasarlanmış olsa da şu an besleyecek veri yok.
2. **`seed_questions` 200/200 vakada boş liste.** Aynı durum.
3. **`difficulty` alanı 200/200 vakada "Intermediate".** Yani zorluk seviyesi şu an ayırt edici bir sinyal taşımıyor; ileride kişiselleştirme/adaptif zorluk düşünülüyorsa bu alanın (LLM ile veya kural tabanlı) yeniden hesaplanması gerekecek.
4. **Branş dağılımı dengesiz:** Gastroenterology (41), Dermatology (36), Neurology (35) en kalabalık; General Internal Medicine/Other yalnızca 6 vaka. Değerlendirme/karşılaştırma deneyleri tasarlanırken (roadmap madde 3-4) bu dengesizlik örneklem seçiminde hesaba katılmalı.
5. **Görsel referans anahtarı uyuşmazlığı** zaten [architecture.md](architecture.md) Bölüm 6, madde 9'da not edilmişti ve ayrı bir arka plan görevinde düzeltildi (`file_path`/`url`/`src` yanına `file` anahtarı eklendi).

---

## 6. Önerilen Sonraki Adımlar

- ~~**(A) Atıf/kaynak gösterimi ekle**~~ **(Tamamlandı — 2026-07-26)** Case detay ekranındaki ("Clinical File" modalı, `chat.js`) rapor görünümüne, kaynak makale başlığı/yazarları/yılı/PMCID/DOI ve lisans adını içeren bir "SOURCE" bölümü eklendi. Canlı olarak tarayıcıda doğrulandı.
- ~~**(B) Lisans/atıf verisini SQL'e taşı**~~ **(Tamamlandı — 2026-07-26)** `Case` tablosuna (`services/models.py`) `source_title`, `source_url`, `source_doi`, `source_authors`, `source_year`, `license_name`, `license_url`, `citation_text` sütunları eklendi. Backfill kaynağı: [`dataset_source_metadata.json`](dataset_source_metadata.json) — bu dosya, mevcut [`dataset_license_audit.json`](dataset_license_audit.json)'daki lisans verisiyle, NCBI'nin `esummary` API'sinden (toplu, ~2 istekte 200 makale) çekilen başlık/yazar/yıl/DOI bilgisinin birleşimi. Migration + backfill script: `medcase-backend/services/backfill_source_metadata.py` (idempotent, `python3 -m services.backfill_source_metadata` ile tekrar çalıştırılabilir). 200/200 vaka için `license_name` ve `citation_text` dolu; API (`GET /cases/{id}`) artık bir `source` alanı döndürüyor; deney çıktılarında (`evaluation/run_experiment.py`) her satırın `license_name`/`citation_text`'i de kayıtlı.
- **(C) Tez metninde netleştirme cümlesi:** Hâlâ öneri — "Veri kümesi MultiCaRe'den (CC0 derleme lisansı) türetilmiştir; ancak kaynak makalelerin %35,5'i yalnızca ticari olmayan kullanıma izin veren CC BY-NC/NC-SA lisanslıdır; proje bitirme tezi kapsamında yalnızca akademik/ticari olmayan amaçla kullanılmaktadır" şeklinde bir paragraf, danışmanın "lisans durumunu netleştir" talebini doğrudan karşılar. Tez metnine eklenmesi kullanıcının kendi kararı.
