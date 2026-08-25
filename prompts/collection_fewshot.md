# Loan Collection Bot - Few-Shot Examples v1.0

## Example 1: Payment Reminder (Routine)
**Context:**
- borrower_name: "Ramesh"
- balance: 42500
- due_date: "2026-07-15"
- case_state: "overdue"
- current_message: "When is my payment due?"

**Assistant Response:**
Hello Ramesh. Your payment of ₹42,500 was due on July 15, 2026. Please make the payment at your earliest convenience to avoid any late fees. Let me know if you need assistance with payment options.

## Example 2: Payment Confirmation (Routine)
**Context:**
- borrower_name: "Priya"
- balance: 18750
- due_date: "2026-08-01"
- case_state: "paid"
- current_message: "I made the payment yesterday. Can you confirm?"

**Assistant Response:**
Yes, Priya. We received your payment of ₹18,750 on July 19, 2026. Your account is now up to date. Thank you for your payment.

## Example 3: Partial Payment Proposal (Complex)
**Context:**
- borrower_name: "Amit"
- balance: 65000
- due_date: "2026-06-30"
- case_state: "negotiating"
- settlement_limit_pct: 25
- current_message: "I can pay half now, can we sort out the rest later?"

**Assistant Response:**
Thank you for reaching out, Amit. I understand you'd like to discuss a partial payment. Your current balance is ₹65,000. Based on our policy, we can accept a settlement of up to 25% (₹16,250) as a one-time offer, or we can discuss a repayment plan. Which option would work better for you?

## Example 4: Dispute (Complex)
**Context:**
- borrower_name: "Sunita"
- balance: 32000
- due_date: "2026-07-10"
- case_state: "disputed"
- current_message: "I never took this loan, this is a mistake. I don't owe you anything."

**Assistant Response:**
I understand your concern, Sunita. According to our records, there is an outstanding balance of ₹32,000 on your account. If you believe this is an error, I can escalate this to our disputes team for a full review. Would you like me to do that?

## Example 5: Settlement Offer (Complex)
**Context:**
- borrower_name: "Vikram"
- balance: 58000
- due_date: "2026-07-01"
- case_state: "negotiating"
- settlement_limit_pct: 25
- current_message: "I can offer 10000 as full settlement. Take it or leave it."

**Assistant Response:**
I appreciate your offer, Vikram. Your current balance is ₹58,000. The maximum settlement we can offer is 25% (₹14,500) as a one-time payment. If you can pay ₹14,500, we can close this account. Please let me know if this works for you.