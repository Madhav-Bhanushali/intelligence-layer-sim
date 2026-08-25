# Intelligence Layer Simulation Trace

**Case ID:** ramesh_negotiation  
**Bot Type:** collection  
**Timestamp:** 2026-08-25T12:33:09.337002  

## 1. Assembled Context

```json
{
  "bot_type": "collection",
  "borrower_name": "Ramesh",
  "balance": 42500,
  "due_date": "2026-07-15",
  "case_state": "negotiating",
  "history": [
    "Reminder sent 2026-07-16",
    "Borrower replied 2026-07-18"
  ],
  "settlement_limit_pct": 20,
  "settlement_offer": 8500,
  "current_message": "I can pay half now, can we sort out the rest later?"
}
```

## 2. Router Decision

**Classification:** complex  
**Reason:** Unauthorized amount: 20.0 (allowed: [8500, 42500])  

## 3. Prompt Version Info

- **system_file:** collection_system.md  
- **system_version:** 778c086a  
- **fewshot_file:** collection_fewshot.md  
- **fewshot_version:** ece2f7ab  

## 4. Model Called

**Model:** openai/gpt-oss-120b (groq)  
**Success:** True  
**Usage:** {'input_tokens': 1191, 'output_tokens': 355}  

## 5. Raw Model Output

```
