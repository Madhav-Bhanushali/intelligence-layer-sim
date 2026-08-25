# Intelligence Layer Simulation Trace

**Case ID:** priya_payment_reminder  
**Bot Type:** collection  
**Timestamp:** 2026-08-25T14:59:26.538046  

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
**Reason:** Matched routine keyword: 'when is my payment'  

## 3. Prompt Version Info

- **system_file:** collection_system.md  
- **system_version:** 778c086a  
- **fewshot_file:** collection_fewshot.md  
- **fewshot_version:** ece2f7ab  

## 4. Model Called

**Model:** mock-haiku (mock)  
**Success:** True  
**Usage:** {'input_tokens': 100, 'output_tokens': 50}  

## 5. Raw Model Output

```
Hello Priya. Your payment of Rs.18,750 was due. Please make the payment at your earliest convenience to avoid any late fees.
```

## 6. Validator Result

**Passed:** True  
**Reason:** All validations passed  

**Details:**

- **amount_check:** True — All amounts match allowed values  
- **tone_check:** True — Tone check passed  
- **distress_check:** True — No distress keywords detected  

## 7. Final Output

```
Hello Priya. Your payment of Rs.18,750 was due. Please make the payment at your earliest convenience to avoid any late fees.
```
