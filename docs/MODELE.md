# Modele AI — inventory i rekomendacje

Stan na 2026-08-21, serwer `llama-local` (`ssh ai`): Ryzen 16C/30 GB RAM,
AMD RX 6950 XT 16 GB VRAM (ROCm w Ollamie — potwierdzone w logach),
Ollama na `0.0.0.0:11434`, ~748 GB wolne.

## Dostępne modele lokalnie

| Model | Rozmiar | Rola w projekcie |
|---|---|---|
| `qwen3:14b` | 9,3 GB | **Rekomendacja na claim reasoning** — mieści się w całości w VRAM z zapasem na kontekst, mocny w structured JSON |
| `gemma3:12b` | 8,1 GB | Kontrast do eksperymentów porównawczych |
| `qwen3:8b` | 5,2 GB | Szybka opcja baseline / smoke-testy |
| Qwen3.8-27B Q3_K_M | 13 GB | Eksperyment jakościowy; Q3 = kompromis jakościowy, VRAM na granicy z ctx 4k |
| `qwen3-coder:30b` | 18 GB | Bez zastosowania tutaj (partial offload = wolny) |

Flota OCR/wizji — patrz [`OCR-BONUS.md`](OCR-BONUS.md).

## Embeddingi (PHASE 10 — RAG, nie teraz)

**Brak modelu embeddingowego na serwerze.** Rekomendacja: **`bge-m3`**
(wielojęzyczny, najlepszy stosunek jakości/ceny dla polskiego retrieval,
~1,2 GB — spokojnie dzieli VRAM z qwen3:14b). Alternatywa: `nomic-embed-text`
(słabszy na PL). Pociągnięcie dopiero przy PHASE 10 i po akceptacji Piotra.

## Jak wybrać model do workflowu

Model jest jednym polem kontraktu AI handlera (`"model": "..."`) — zmiana
modelu nie wymaga dotykania workflowu. Decyzja należy do Piotra.
Eksperymenty porównawcze (ten sam dataset + różne modele) → PHASE 11.

## OpenRouter

Alternatywa chmurowa dla porównań (PHASE 11). Piotr podłącza konto/klucz
później; handler wołany byłby z tym samym kontraktem przez inny backend
lub bezpośredni HTTP node. Do MVP niepotrzebny.
