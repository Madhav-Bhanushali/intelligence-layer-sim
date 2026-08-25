# Intelligence Layer Simulation Trace

**Case ID:** priya_payment_reminder  
**Bot Type:** collection  
**Timestamp:** 2026-08-25T12:32:30.189017  

## 1. Assembled Context

```json
{
  "bot_type": "collection",
  "borrower_name": "Priya",
  "balance": 18750,
  "due_date": "2026-08-01",
  "case_state": "overdue",
  "history": [
    "Payment due 2026-07-25",
    "First reminder sent 2026-07-28"
  ],
  "settlement_limit_pct": 15,
  "settlement_offer": 2812,
  "current_message": "When is my payment due?"
}
```

## 2. Router Decision

**Classification:** routine  
**Reason:** Unauthorized amount: 1.0 (allowed: [2812, 18750]); Unauthorized amount: 2026.0 (allowed: [2812, 18750])  

## 3. Prompt Version Info

- **system_file:** collection_system.md  
- **system_version:** 778c086a  
- **fewshot_file:** collection_fewshot.md  
- **fewshot_version:** ece2f7ab  

## 4. Model Called

**Model:** openai/gpt-oss-20b (groq)  
**Success:** True  
**Usage:** {'input_tokens': 1182, 'output_tokens': 196}  

## 5. Raw Model Output

```
