from typing import Tuple


COLLECTION_COMPLEX_KEYWORDS = [
    "negotiate", "negotiation", "settlement", "settle", "partial payment",
    "half", "part pay", "installment", "repayment plan", "payment plan",
    "dispute", "disputed", "mistake", "never took", "don't owe", "error",
    "object", "objection", "refuse", "refusing", "can't pay", "cannot pay",
    "lost job", "unemployed", "hardship", "difficult", "waive", "waiver",
    "reduce", "reduction", "forgive", "forgiveness", "write off"
]

COLLECTION_ROUTINE_KEYWORDS = [
    "when is my payment", "due date", "payment due", "confirm", "confirmation",
    "paid", "made payment", "payment made", "receipt", "thank you"
]

MARKETING_COMPLEX_KEYWORDS = [
    "customized", "custom", "tailored", "personalized", "my profile",
    "my situation", "specific", "specific situation", "explain", "details",
    "terms", "repayment terms", "processing fee", "fees", "how does",
    "what are", "tell me about", "compare", "difference", "better",
    "best", "recommend", "suggest", "advice", "need", "requirement",
    "business", "manufacturing", "machinery", "doctor", "profession",
    "interest rate", "how fast", "how quickly", "disbursal", "disbursement",
    "approved", "approval", "document", "documents", "eligibility criteria"
]

MARKETING_ROUTINE_KEYWORDS = [
    "offer", "notification", "what is this", "about this", "eligible",
    "eligibility", "pre-approved", "preapproved", "announcement"
]


def classify_collection(message: str) -> Tuple[str, str]:
    """Classify a collection bot message as routine or complex."""
    message_lower = message.lower()
    
    for keyword in COLLECTION_COMPLEX_KEYWORDS:
        if keyword in message_lower:
            return "complex", f"Matched complex keyword: '{keyword}'"
    
    for keyword in COLLECTION_ROUTINE_KEYWORDS:
        if keyword in message_lower:
            return "routine", f"Matched routine keyword: '{keyword}'"
    
    return "routine", "No complex keywords matched, defaulting to routine"


def classify_marketing(message: str) -> Tuple[str, str]:
    """Classify a marketing bot message as routine or complex."""
    message_lower = message.lower()
    
    for keyword in MARKETING_COMPLEX_KEYWORDS:
        if keyword in message_lower:
            return "complex", f"Matched complex keyword: '{keyword}'"
    
    for keyword in MARKETING_ROUTINE_KEYWORDS:
        if keyword in message_lower:
            return "routine", f"Matched routine keyword: '{keyword}'"
    
    return "routine", "No complex keywords matched, defaulting to routine"


def route_message(bot_type: str, message: str) -> Tuple[str, str]:
    """
    Route a message to routine or complex based on bot type.
    Returns (classification, reason).
    """
    if bot_type == "collection":
        return classify_collection(message)
    elif bot_type == "marketing":
        return classify_marketing(message)
    else:
        raise ValueError(f"Unknown bot_type: {bot_type}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python model_router.py <bot_type> <message>")
        sys.exit(1)
    
    bot_type = sys.argv[1]
    message = " ".join(sys.argv[2:])
    
    classification, reason = route_message(bot_type, message)
    print(f"Classification: {classification}")
    print(f"Reason: {reason}")