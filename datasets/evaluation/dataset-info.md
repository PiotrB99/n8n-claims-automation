# Dataset ewaluacji natywnej (PHASE 8)

- Data Table n8n: **eval_dataset_v0** (id 859293e8-c7ac-4a04-9ab0-3f08d4ca9b80)
- 40 wierszy: input_file, case_id, expected_decision, requires_human
- Kolumny wynikowe (wypełnia workflow claims-demo-eval-native przez Evaluation/setOutputs):
  got_decision, decision_ok
- Workflow: **claims-demo-eval-native** (bO6br9QIwBHD7yqa):
  Eval Trigger (Data table) → Execute Workflow (happy path) → Read result file → Parse → Evaluation

## Uruchomienie

1. Otwórz claims-demo-eval-native w n8n i kliknij „Execute workflow"
   (albo zakładka Evaluations → Run).
2. Trigger pobiera 40 wierszy z eval_dataset_v0; każda linia przechodzi przez happy path.
3. Po zakończeniu kolumny got_decision/decision_ok są wypełnione w Data Table.

Uwaga: REST API evaluacji (odpalanie/odczyt runów przez MCP) wymaga n8n ≥ 2.30/2.32 —
na 1.121.3 run startuje się z UI, a wyniki czyta się z tabeli datasetu.
