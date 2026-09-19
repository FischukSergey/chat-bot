# Прогон золотого набора (2026-09-19)

Эталоны: `data/eval/gold.yaml` ← `БДР для индексации.xlsx`.
Живой MCP + `qwen/qwen3.6-35b-a3b`. **22 pass / 3 fail / 25.**

Типы (бюджет, не договоры): код статьи, ветка, остаток, факт vs принятые, отказ, сквозной/kind.

| id | тип | ok | провал |
|---|---|---|---|
| code-1.8.2 | code | PASS | |
| code-1.8.3 | code | PASS | |
| code-1.8.1 | code | PASS | |
| branch-1.8 | branch | FAIL | пустой текст после `budget_summary` |
| remain-1.8.2 | remain | PASS | |
| fact-vs-1.8.2 | fact_vs_accepted | PASS | |
| refuse-9.9.9 | refuse | PASS | |
| refuse-99.99 | refuse | PASS | |
| refuse-quantum | refuse | FAIL | отказ есть, но свалка чужих сумм (транспорт) |
| refuse-contract | refuse | PASS | |
| cross-energy-prod | cross | PASS | |
| kind-energy-mgmt | kind | PASS | |
| cross-water-prod | cross | PASS | |
| cross-rent-pipes | cross | FAIL | пустой текст после tools (ветка-родитель) |
| code-5.1.1.1 | code | PASS | |
| code-5.1.2 | code | PASS | |
| remain-guard | remain | PASS | |
| fact-vs-payroll | fact_vs_accepted | PASS | |
| branch-5.1 | branch | PASS | |
| code-1.5 | code | PASS | |
| code-5.6.1 | code | PASS | |
| code-zero-rent-auto | code | PASS | |
| kind-mgmt-fot | kind | PASS | |
| remain-1.5 | remain | PASS | |
| refuse-contract-roma | refuse | PASS | |

Выдуманных сумм на PASS-кейсах нет. Факт / принятые / `remain_free` на живой смете `null` — модель не подставила лимит как остаток.

Полные ответы: `data/eval/last-run.yaml`. Повтор: `task assistant -- eval`.
