# Intelligence Layer Simulation Trace

**Case ID:** sneha_tailored_pitch  
**Bot Type:** marketing  
**Timestamp:** 2026-08-25T12:33:20.601532  

## 1. Assembled Context

```json
{
  "bot_type": "marketing",
  "lead_name": "Sneha",
  "product": "Personal Loan",
  "interest_rate": "10.9%",
  "max_amount": 300000,
  "eligibility_score": "high",
  "history": [],
  "current_message": "I'm a doctor with a stable income. Can you give me a customized offer based on my profile?"
}
```

## 2. Router Decision

**Classification:** complex  
**Reason:** Unauthorized amount: 3.0 (allowed: [10.9, 300000]); Unauthorized amount: 24.0 (allowed: [10.9, 300000])  

## 3. Prompt Version Info

- **system_file:** marketing_system.md  
- **system_version:** 3bcb3c95  
- **fewshot_file:** marketing_fewshot.md  
- **fewshot_version:** cc22fac6  

## 4. Model Called

**Model:** openai/gpt-oss-120b (groq)  
**Success:** True  
**Usage:** {'input_tokens': 1225, 'output_tokens': 206}  

## 5. Raw Model Output

```
