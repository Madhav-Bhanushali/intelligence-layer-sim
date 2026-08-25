# Intelligence Layer Simulation Trace

**Case ID:** rohit_eligibility_check  
**Bot Type:** marketing  
**Timestamp:** 2026-08-25T12:21:49.483782  

## 1. Assembled Context

```json
{
  "bot_type": "marketing",
  "lead_name": "Rohit",
  "product": "Car Loan",
  "interest_rate": "9.25%",
  "max_amount": 1000000,
  "eligibility_score": "high",
  "history": [],
  "current_message": "Am I eligible for a car loan?"
}
```

## 2. Router Decision

**Classification:** routine  
**Reason:** Matched routine keyword: 'eligible'  

## 3. Prompt Version Info

- **system_file:** marketing_system.md  
- **system_version:** 3bcb3c95  
- **fewshot_file:** marketing_fewshot.md  
- **fewshot_version:** cc22fac6  

## 4. Model Called

**Model:** mock-haiku (mock)  
**Success:** True  
**Usage:** {'input_tokens': 100, 'output_tokens': 50}  

## 5. Raw Model Output

```
Hi Rohit! Based on your profile, you have a high eligibility score for our Car Loan. The interest rate is 9.25% with a maximum amount of Rs.1,000,000. You're pre-qualified to apply.
```

## 6. Validator Result

**Passed:** True  
**Reason:** All validations passed  

**Details:**

- **amount_check:** True — All amounts match allowed values  
- **tone_check:** True — Tone check passed  

## 7. Final Output

```
Hi Rohit! Based on your profile, you have a high eligibility score for our Car Loan. The interest rate is 9.25% with a maximum amount of Rs.1,000,000. You're pre-qualified to apply.
```
