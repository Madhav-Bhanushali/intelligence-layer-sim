import re
from typing import Dict, Any, List, Set


COLLECTION_BANNED_WORDS = [
    "threaten", "legal action", "court", "sue", "lawsuit",
    "seize", "repossess", "arrest", "police", "criminal",
    "fraud", "harass", "harassment", "ruin", "destroy"
]

COLLECTION_DISTRESS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "self harm",
    "hopeless", "desperate", "can't go on", "give up"
]

MARKETING_BANNED_WORDS = [
    "guarantee", "guaranteed", "no risk", "risk-free",
    "instant approval", "guaranteed approval", "no questions asked",
    "0%", "zero percent", "zero interest", "no interest ever",
    "unlimited", "no limit"
]


def extract_amounts(text: str) -> List[float]:
    """
    Extract monetary amounts from text.
    Handles formats like: ₹42,500, 42500, 42,500, Rs. 42500, etc.
    """
    patterns = [
        r"₹\s*([\d,]+\.?\d*)",
        r"Rs\.?\s*([\d,]+\.?\d*)",
        r"INR\s*([\d,]+\.?\d*)",
        r"\b([\d]{1,3}(?:,[\d]{3})*(?:\.\d+)?)\b",
        r"\b(\d{4,})\b",
    ]
    
    amounts = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                clean = match.replace(",", "")
                amounts.append(float(clean))
            except ValueError:
                pass
    
    return list(set(amounts))


def extract_percentage(text: str) -> List[float]:
    """Extract percentage values from text."""
    pattern = r"(\d+\.?\d*)\s*%"
    matches = re.findall(pattern, text)
    return [float(m) for m in matches]


def validate_amounts(
    output: str,
    context: Dict[str, Any],
    bot_type: str
) -> Dict[str, Any]:
    """Validate that all amounts in output match allowed values from context."""
    extracted_amounts = extract_amounts(output)
    extracted_pcts = extract_percentage(output)
    
    allowed_amounts = set()
    allowed_pcts = set()
    
    if bot_type == "collection":
        allowed_amounts.add(context.get("balance", 0))
        allowed_amounts.add(context.get("settlement_offer", 0))
        allowed_pcts.add(context.get("settlement_limit_pct", 0))
    elif bot_type == "marketing":
        max_amount = context.get("max_amount", 0)
        allowed_amounts.add(max_amount)
        interest_rate_str = context.get("interest_rate", "0%")
        try:
            interest_pct = float(interest_rate_str.replace("%", ""))
            allowed_pcts.add(interest_pct)
            # Also allow the numeric interest rate as an amount (in case model omits %)
            allowed_amounts.add(interest_pct)
        except ValueError:
            pass
    
    violations = []
    
    for amt in extracted_amounts:
        if amt not in allowed_amounts and amt not in [0]:
            violations.append(f"Unauthorized amount: {amt} (allowed: {sorted(allowed_amounts)})")
    
    for pct in extracted_pcts:
        if pct not in allowed_pcts and pct not in [0]:
            violations.append(f"Unauthorized percentage: {pct}% (allowed: {sorted(allowed_pcts)}%)")
    
    if violations:
        return {"passed": False, "reason": "; ".join(violations)}
    
    return {"passed": True, "reason": "All amounts match allowed values"}


def check_tone(output: str, bot_type: str) -> Dict[str, Any]:
    """Check for banned words/phrases in the output."""
    output_lower = output.lower()
    banned_words = COLLECTION_BANNED_WORDS if bot_type == "collection" else MARKETING_BANNED_WORDS
    
    violations = []
    for word in banned_words:
        if word.lower() in output_lower:
            violations.append(f"Banned word/phrase detected: '{word}'")
    
    if violations:
        return {"passed": False, "reason": "; ".join(violations)}
    
    return {"passed": True, "reason": "Tone check passed"}


def check_distress(output: str) -> Dict[str, Any]:
    """Check for distress keywords (collection bot only)."""
    output_lower = output.lower()
    
    for keyword in COLLECTION_DISTRESS_KEYWORDS:
        if keyword in output_lower:
            return {"passed": False, "reason": f"Distress keyword detected: '{keyword}'"}
    
    return {"passed": True, "reason": "No distress keywords detected"}


def validate_output(output: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run all validations on the model output.
    Returns a combined result.
    """
    bot_type = context.get("bot_type", "collection")
    
    amount_check = validate_amounts(output, context, bot_type)
    tone_check = check_tone(output, bot_type)
    
    all_checks = [amount_check, tone_check]
    
    if bot_type == "collection":
        distress_check = check_distress(output)
        all_checks.append(distress_check)
    
    for check in all_checks:
        if not check["passed"]:
            return {
                "passed": False,
                "reason": check["reason"],
                "details": {
                    "amount_check": amount_check,
                    "tone_check": tone_check,
                    **({"distress_check": distress_check} if bot_type == "collection" else {})
                }
            }
    
    return {
        "passed": True,
        "reason": "All validations passed",
        "details": {
            "amount_check": amount_check,
            "tone_check": tone_check,
            **({"distress_check": distress_check} if bot_type == "collection" else {})
        }
    }


if __name__ == "__main__":
    import sys
    import json
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from context_assembler import assemble_context, load_case
    
    if len(sys.argv) < 4:
        print("Usage: python output_validator.py <bot_type> <case_id> <output_text>")
        sys.exit(1)
    
    bot_type = sys.argv[1]
    case_id = sys.argv[2]
    output_text = " ".join(sys.argv[3:])
    
    case = load_case(bot_type, case_id)
    context = assemble_context(case)
    
    result = validate_output(output_text, context)
    print(json.dumps(result, indent=2))