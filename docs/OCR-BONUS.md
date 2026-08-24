# OCR / wizja jako wyróżnik projektu (po MVP)

Pomysł z rozpoznania serwera (2026-08-21): na `llama-local` stoi nieużywana
flota modeli OCR/wizji, która idealnie pasuje do scenariusza z guide §3 —
„klient przesyła zdjęcia uszkodzonej paczki".

## Co jest dostępne

| Model | Rozmiar | Zastosowanie |
|---|---|---|
| `qwen3-vl:8b` | 6,1 GB | Opis zdjęć uszkodzeń (dowody fotograficzne) |
| `numind/nuextract3` (Q4/Q6) | 3,4–4,1 GB | Ekstrakcja structured data z dokumentów (potwierdzenia dostawy, faktury) |
| `deepseek-ocr`, `olmocr2:7b` | 6,7–9,5 GB | OCR zeskanowanych dokumentów |
| `minicpm-v`, `qwen2.5vl:7b` | 5,5–6 GB | Alternatywy wizyjne do porównań |

## Scenariusz docelowy

1. Mock email ma załączniki (v0.1: opisane słownie w JSON).
2. Później: realny plik → qwen3-vl opisuje uszkodzenie → nuextract wyciąga
   pola z dokumentu → wynik jako **evidence** w structured output LLM.
3. Ewaluacja „evidence correctness" (guide §23) dostaje wtedy prawdziwe
   znaczenie: czy system poprawnie odczytał dowód, zanim na nim zadecydował.

## Dlaczego to wyróżnia projekt

Większość demo „AI + reklamacje" operuje na czystym tekście. Dodanie ścieżki
multimodalnej (zdjęcia → structured evidence → decyzja) pokazuje pełny łańcuch
integracji. Koszt: jeden dodatkowy odgałęzienie workflow + ewaluacja.

## Status

Poza MVP. Kandydat na fazę po PHASE 10 (RAG), razem z rozszerzeniem datasetu
o realne pliki załączników. Wymaga: przesyłania obrazów do Ollamy (handler
dzieli tylko tekst — trzeba dodać ścieżkę albo wołać Ollamę bezpośrednio
z claim workflow dla tej gałęzi).
