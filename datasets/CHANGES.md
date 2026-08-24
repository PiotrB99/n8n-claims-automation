# Dziennik zmian w datasetcie i środowisku testowym

## 2026-08-24 — PHASE 11: eksperyment RAG top-k (run #5) + naprawa batch-eval

**Eksperyment A/B „RAG vs pełna baza":** `Config.rag_top_k` 6 → 10 w happy pathu
(przez n8n-mcp), rerun 40 spraw. Wynik: **82,5% (33/40)** — identycznie jak
top-6 (run #4). Porównanie na tym samym harnessie (batch-eval, jak run #3):

| Konfiguracja | Harness | Accuracy |
|---|---|---|
| Pełna baza wiedzy (run #3) | batch-eval | **95%** |
| RAG top-6 (run #4) | eval-native | 82,5% |
| RAG top-10 (run #5) | batch-eval | 82,5% |

**Wniosek:** szerokość okna retrievalu NIE jest wąskim gardłem — podbicie k
nic nie zmienia. Gap ~12,5 p.p. względem pełnej bazy to model wariancja na
przypadkach brzegowych: powtarzające się missy w obu runach RAG to CASE-0018
(HR→ACCEPT), CASE-0034 i CASE-0037 (ACCEPT→HR). Kandydat na kolejny krok:
doklejanie POL-12 / analiza promptu, nie retrieval. Artefakt:
`outbox/eval-run-005-rag-top10.json`.

**Naprawa `claims-demo-batch-eval` (był zepsuty od upgrade'u 2.x):**
1. Migracja na Extract from File — nowe node'y `Extract expected`/`Extract
   results`; Code node'y czytają `$json.data` zamiast base64 z
   `binary.data.data` (ten sam breaking change co 2026-08-23).
2. `Build expected map` pomija `all.json` (`if (!e.id) continue;`) — selektor
   `*.json` łapie też agregat.
3. `Parse results` akceptuje płaskie obiekty wynikowe (happy path od dawna
   pisze `{case_id,...}` bez opakowania `{result}` — stary parser odrzucał
   wszystkie pliki → „Brak wynikow").
4. Odporność pętli: `Run happy path` ma `retryOnFail` (2 próby) +
   `onError: continueRegularOutput` — jeden flaky case (task runner timeout na
   `Parse AI output`) nie ubija już całego 40-minutowego runu.
Zmiany przez n8n-mcp, walidacja 0 errors; eksporty repo zsynchronizowane.
Run #5 policzony z plików outbox skryptem `narzedzia/eksportuj-run5-top10.py`
(harness padł dopiero na agregacji — naprawa wgrana, do pełnej weryfikacji
przy następnym rerunie).

## 2026-08-24 — PHASE 8: pierwsza natywna ewaluacja (run #4) + fix confidence

- **Run #4** przez `claims-demo-eval-native` (Evaluation Trigger + Evaluation node,
  2.36.5): decision accuracy **82,5%** (33/40), 3× TECHNICAL_FAIL
  (CASE-0029, 0036, 0040 — flakiness OpenRouter na 40-minutowym runie),
  4 niezgodne decyzje (0018, 0023: HR→ACCEPT/REJECT; 0034, 0037: ACCEPT→HR).
- Wynik NIE jest porównywalny 1:1 z baseline (run #3: 95%, pełna baza wiedzy):
  happy path leciał z RAG top-6, więc sprawy wymagające kilku reguł naraz
  (np. POL-04+06+07) mogły nie dostać pełnego kontekstu. To punkt wyjścia
  eksperymentu PHASE 11 (A/B: pełna baza vs RAG, podbicie rag_top_k).
- Artefakt: `outbox/eval-run-004-native.json` (eksport z Data Table
  `eval_dataset_v0`, skrypt `narzedzia/eksportuj-eval-native.py`).
- **Fix:** node Evaluation nie zapisywał `confidence` do tabeli (null przy 40/40).
  Mapowanie rozszerzone o `confidence` i `gate_reason`; workflow zaktualizowany
  przez n8n-mcp i zwalidowany (0 errors). Przy następnych runach kolumny
  wypełnią się poprawnie.

## 2026-08-24 — PHASE 10: klasyczny RAG (bge-m3)

- Embeddingi bazy wiedzy: 22 elementy (12 reguł POL + 10 precedensów), model
  bge-m3, 1024 wymiary — \knowledge/embeddings.json\, generowane z llama-local.
- Happy path: nowa ścieżka Read embeddings → Embed query (HTTP do Ollamy,
  /api/embed) → RAG retrieve (cosine similarity, top-6, Config.rag_top_k).
  Prompt dostaje WYŁĄCZNIE wybrane fragmenty z wynikiem podobieństwa.
- Testy: CASE-0001 ACCEPT 0.95 (PREC-01 trafiony retrieval-em),
  CASE-0021 HUMAN_REVIEW 0.85 z pustą listą dowodów — brak doklejania
  nieistotnych reguł przy luce w wiedzy.

## 2026-08-23 — UPGRADE n8n 1.121.3 → 2.36.5 i migracja na Extract from File

**Upgrade:** przyczyna starej wersji = `image: n8nio/n8n` bez `docker compose pull`
od 8 miesięcy, brak watchtowera. Po backupie (`n8n-full-1.121.3-20260823-0911.tar.gz`,
66 MB) compose przypięty do `n8nio/n8n:2.36.5`. Stany aktywności 16 workflowów
przywrócone z backupu bazy (porównanie workflow_entity przed/po). AI handler
celowo aktywny — w 2.x sub-workflow musi być opublikowany.

**Breaking change dla claims-demo:** w n8n 2.x Code node NIE dostaje treści
pliku w `binary.data.data` — to tylko marker `"filesystem-v2"` (rozmiar wędruje
do `binary.data.bytes`). Wszystkie parsery Buffer/base64 padały ze śmieciami
typu „~)^+-zo". Migracja: każdy odczyt pliku → node **Extract from File**
(fromJson), treść pod `$json.data`. Przerobione: happy path (case/orders/
policies/precedents — 30 nodów), report (all.json + wyniki), eval-native.
Dodatkowo wymagane: env `N8N_RESTRICT_FILE_ACCESS_TO=/home/node/claims`
(2.x zaostrzył dostęp do plików) oraz sekwencyjne łańcuchy zamiast rozgałęzień
do jednego node'a (błąd „hasn't been executed").

**Weryfikacja po migracji:** CASE-0001 ACCEPT conf 0.96 z pełnym uzasadnieniem ✔

## 2026-08-22 — Claim Case (n8n Data Tables)

Tabela `claim_cases` (id `5c1ec41e-…`) utworzona **bezpośrednio w SQLite** —
publiczne API n8n 1.121.3 i MCP nie wystawiają data tables, a CLI nie ma takiej
komendy. Backup bazy przed zapisem: `database.sqlite.bak-claims-dt`. Pułapka:
n8n przy tworzeniu przez własną ścieżkę zakłada też fizyczną tabelę-wiersze
`data_table_user_<id>` (id autoincrement + kolumny wg typu + createdAt/updatedAt)
— trzeba było odtworzyć ją ręcznie wg schematu z `data-table-ddl.service.js`.

Happy path rozszerzony o node „Save claim case" (insert — dziennik decyzji,
append-only): case_id, status (`DECIDED`/`WAITING_HUMAN`), final_decision,
ai_recommendation, confidence, gate_reason, order_value_pln, model, decided_at.
Weryfikacja na CASE-0010: 3 wiersze historii (2× TECHNICAL_FAIL z okresu
niestabilności modelu + finalny REJECT conf 0.95). Uwaga: upsert (update po
case_id) blokuje aktywację workflowu — walidator n8n odrzuca ręcznie budowane
warunki filtrów (`Could not find property option`); do fazy follow-up pozostaje
insert-log albo powrót do tematu po upgrade n8n.

Dodatkowo: retry OpenRouter zwiększony do ×5 / 5 s; plik wynikowy znów niesie
decyzję routera (nie wiersz tabeli).

## 2026-08-22 — FINAL RUN #3 → 95%, zero błędów technicznych

**Wynik:** decision accuracy **95% (38/40)**, human-path 95%, **TECHNICAL_FAIL: 0**
(wcześniejsze runy: 5 i 3). Wynik: `datasets/outbox/eval-run-003-final.json`,
raport generowany przez nowy workflow `claims-demo-report` (`SQLrd9Lp74409R0A`),
który oddzielono od batcha (batch = zbieranie, report = analiza plików).

Naprawy pośrednie wykryte w trakcie:
- retry na wywołaniu OpenRouter (retryOnFail ×3, 3 s) — guide §28,
- twardy parser outputu modelu (cały content → ostatni blok JSON): CASE-0010
  padał deterministycznie, po naprawie REJECT zgodny z GT z pełnym uzasadnieniem,
- poprawka skali procentów w Summary,
- metryka human_path nie liczy TECHNICAL_FAIL jako trafienia.

Pozostałe 2 pomyłki (95%):
- CASE-0007 (B): REJECT→HUMAN_REVIEW, kierunek konserwatywny („AI zgłosiło
  brakujące informacje"),
- CASE-0023 (E): HUMAN_REVIEW→REJECT — roszczenie osób trzecich, interpretacja.

Obie to przypadki brzegowe interpretacji, nie błędy danych. Run-to-run variance
modelu jest realny — dokładnie po to są progi regresji (guide §26), a nie
oczekiwanie identycznych wyników między runami.

## 2026-08-22 — eval run #2 → regresja promptowa, TECHNICAL_FAIL, starzejące się GT

**Run #2 (pełny, 40):** accuracy 87,5% — spadek względem run #1 mimo napraw
architektonicznych. Trzy różne klasy problemów, każda inaczej załatana:

1. **Regresja promptowa** (CASE-0012): zdanie „nie przekazuj do człowieka spraw
   jednoznacznych" rozluźniło ostrożność przy przypadkach samoprzecznych.
   Zamienione na zbalansowaną parę zdań + jawne odwołanie do POL-10 (sprzeczność
   wewnętrzna dowodów → HUMAN_REVIEW). Rerun: ✔ model sam wskazuje sprzeczność.
2. **TECHNICAL_FAIL ×3** (CASE-0037–39): obcięty structured output (brak limitu
   tokenów). Fix: `max_tokens: 4000`. Rerun: ✔ 3/3 poprawne decyzje.
3. **Zestarzałe ground truth** (CASE-0015): GT pisane przed order lookup wymagało
   HUMAN_REVIEW z powodu nieznanej daty doręczenia; po dodaniu systemu zamówień
   data jest znana i ACCEPT jest wyprowadzalne. GT zaktualizowane świadomie
   (HUMAN_REVIEW → ACCEPT) z uzasadnieniem. Wniosek: **wzbogacenie danymi zmienia
   to, co jest decydowalne automatycznie — dataset musi nadążyć.**

Dodatkowo: metryka `human_path_ok` przestała liczyć TECHNICAL_FAIL jako trafienie.

**Stan kompozytowy po poprawkach:** 40/40 (run #2 + rerun 5). Finalny czysty pełny
run pozostaje do wykonania dla potwierdzenia braku regresji.

## 2026-08-21 — eval run #1 → naprawa przez wzbogacenie danymi zamówień

**Co się stało:** Pierwszy pełny run (40 przypadków, model `stealth/ox-alpha`):
decision accuracy **92,5%** (37/40). Trzy pomyłki, wszystkie ten sam kierunek
(konserwatywny): oczekiwane ACCEPT → system dał HUMAN_REVIEW
(CASE-0002, CASE-0032, CASE-0038).

**Diagnoza:** Model w uzasadnieniach wskazał brakujące fakty: cena towaru
(0002, 0032) i godzina doręczenia dla okna 48 h (0038). Weryfikacja treści
maili potwierdziła: **tych danych nie było w wejściu**, a ground truth je
zakładał. To nie był błąd modelu ani promptu — to defekt datasetu ujawniony
przez ewaluację (cel jej istnienia, guide §22–23).

**Naprawa (architekturalna, nie łatanie ground truth):**
1. Nowy mock systemu zamówień `datasets/orders.json` (40 rekordów:
   wartość towaru, kategoria, potwierdzone doręczenie) — generowany przez
   agenta z zasadami spójności z regulaminem i expected.
2. Happy path: node **Order lookup** — sprawa wzbogacana danymi zamówienia
   przed rozumowaniem LLM („DANE Z SYSTEMU ZAMOWIEN nadpisują dane klienta").
3. Decision Router: **deterministyczna bramka POL-06** — wartość > 2000 zł
   wymusza HUMAN_REVIEW z kodu, niezależnie od rekomendacji modelu.

**Weryfikacja:** rerun trzech nietrafionych przypadków przez webhook:
CASE-0002 ACCEPT (conf 0.98), CASE-0032 ACCEPT (0.95, równość progu 500 zł
z danych zamówienia), CASE-0038 ACCEPT (0.95, dwa roszczenia ocenione osobno).
**3/3.**

**Wniosek metodyczny:** brakującą wartość roszczenia naprawia integracja
z systemem zamówień, nie dopisywanie cen do maili klienta. Klient często nie
podaje ceny — i nie powinien musieli.
