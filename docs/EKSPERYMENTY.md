# Eksperymenty — metodologia i wyniki

Dokument opisuje, jak mierzona jest jakość decyzji silnika reklamacji i co
wynikają z przeprowadzonych eksperymentów. Uzupełnienie README o kontekst
inżynierski: nie tylko „ile procent", ale **dlaczego** taki wynik i co z niego
wynika.

## Dataset

- 40 mockowych zgłoszeń klientów (`datasets/inbox/CASE-0001..0040.json`):
  uszkodzona przesyłka, brakujący element, zły towar, zaginięcie przesyłki,
  roszczenia osób trzecich, nadużycia, sprawy wielooznaczne.
- Ground truth per przypadek (`datasets/expected/`): oczekiwana decyzja
  (`ACCEPT` / `REJECT` / `HUMAN_REVIEW`), flaga `requires_human`, referencje
  do reguł.
- Dataset wygenerował **izolowany agent**, który dostał tylko specyfikację
  domeny i formatów — bez wiedzy o implementacji. Dzięki temu przypadki nie są
  „nacechowane" znajomością rozwiązania (antywzorzec: testy pisane przez autora
  kodu).
- Grupy A–H po 5 przypadków pozwalają lokalizować spadki jakości per kategoria.

## Metryki

- **Decision accuracy** — udział przypadków, gdzie `final_decision ==
  expected_decision`. `TECHNICAL_FAIL` (błąd techniczny, np. timeout API)
  liczy się jako błąd — w produkcji też byłby to zły wynik dla klienta.
- **Human-path accuracy** — czy przypadki wymagające człowieka faktycznie
  trafiły do review, a automatyczne przeszły bez człowieka.

## Dwa harnessy ewaluacyjne

| | batch-eval | eval-native |
|---|---|---|
| Mechanizm | webhook → pętla 40 spraw przez happy path → raport accuracy | natywny n8n Evaluations (Evaluation Trigger + node Evaluation) |
| Zapis wyników | pliki outbox + `eval-report.json` | Data Table `eval_dataset_v0` (per przypadek) |
| Zastosowanie | baseline i regresja | demonstracja wbudowanego mechanizmu n8n |

Oba harnessy wołają ten sam happy path, więc decyzje są porównywalne;
różni się sposób zbierania wyników.

## Historia runów

### Run #1–#2: ewaluacja jako narzędzie diagnozy (92,5% → 95%)

Pierwszy pełny run wykazał 3 błędy, wszystkie jeden kierunek (konserwatywny):
oczekiwane ACCEPT → system dał HUMAN_REVIEW. Diagnoza z uzasadnień modelu:
**w danych wejściowych nie było ceny towaru ani godziny doręczenia**, a ground
truth je zakładał. To defekt datasetu, nie modelu.

Naprawa była architektoniczna: mock systemu zamówień (`datasets/orders.json`)
+ node Order lookup wzbogacający sprawę przed rozumowaniem LLM. Dodatkowo
Decision router dostał deterministyczną bramkę POL-06 (zamówienie > 2000 zł ⇒
human review z kodu). Wniosek metodyczny: brakujących danych nie naprawia się
dopisywaniem ich do maili klienta, tylko integracją z systemem źródłowym.

### Run #3: baseline 95% (38/40, 0 TECHNICAL_FAIL)

Pełna baza wiedzy (12 reguł + 10 precedensów) w całości w promptcie.

### Run #4–#5: eksperyment RAG A/B (82,5%)

Pytanie badawcze: *czy klasyczny RAG (embeddingi bge-m3, cosine similarity,
top-k fragmentów doklejanych do promptu) utrzyma jakość decyzji?*

| Run | rag_top_k | Harness | Accuracy |
|---|---|---|---|
| #4 | 6 | eval-native | 82,5% (33/40, 3× TECHNICAL_FAIL) |
| #5 | 10 | batch-eval | 82,5% (33/40, 2× TECHNICAL_FAIL) |

Wnioski:

1. **RAG kosztuje ~12 p.p.** względem pełnej bazy — przy KB tak małej, że
   mieści się w kontekście w całości. Retrieval wyrzuca reguły, które okazałyby
   się istotne dopiero w toku rozumowania (np. reguła o nadużyciu przy sprawie,
   która na pierwszy rzut oka wygląda standardowo).
2. **Podbicie top-6 → top-10 nie zmieniło nic.** Szerokość okna nie jest
   wąskim gardłem. Powtarzające się missy obu runów to te same przypadki
   brzegowe: CASE-0018 (oczekiwane HR, system ACCEPT), CASE-0034 i CASE-0037
   (oczekiwane ACCEPT, system HR). Model raz jest ostrożny, raz nie — to
   wariancja na granicy decyzyjnej, nie brak reguł w promptcie.
3. Hipoteza na kolejny eksperyment: **zawsze doklejaj regułę fallback POL-12**
   (oraz reguły o nadużyciu POL-10) niezależnie od wyniku retrievalu; alternatywnie
   chunkless RAG — retriewal po ustrukturyzowanych polach (kategoria, wartość,
   termin) zamiast podobieństwa tekstu.

### Run #6+: porównanie modeli LLM

*(sekcja uzupniana w toku eksperymentu)*

Plan: ten sam pipeline i dataset, różne modele w nodzie Config — model
chmurowy przez OpenRouter vs model lokalny (Ollama, qwen3:14b). Kryteria:
decision accuracy, liczba TECHNICAL_FAIL, stabilność (powtarzalność decyzji
na przypadkach brzegowych).

## Regresja

Workflow `claims-demo-report` liczy accuracy z plików wynikowych (bez wołania
LLM-a) i porównuje z progiem z konfiguracji. Docelowo: uruchomienie po każdej
zmianie promptu/reguł, PASS/WARNING/FAIL jak w CI.

## Ograniczenia (uczciwie)

- Jeden run = jedna próba; na 40 przypadkach różnica kilku p.p. może być
  wariancją. Wnioski wyciągamy z powtarzających się wzorców (te same przypadki,
  ten sam kierunek błędu), nie z pojedynczej liczby.
- Dataset mockowy, po polsku, domena e-commerce. Generalizacja na inne domeny
  wymaga własnego datasetu — sam mechanizm (harness, bramki, Claim Case) jest
  niezależny od domeny.
