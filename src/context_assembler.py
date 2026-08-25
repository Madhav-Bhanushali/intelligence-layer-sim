import json
from typing import Dict, Any


def assemble_context(case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merges mock case data into a structured context object.
    Pure data merging - no generation logic.
    """
    bot_type = case.get("bot_type", "collection")
    
    if bot_type == "collection":
        context = {
            "bot_type": "collection",
            "borrower_name": case.get("borrower_name", ""),
            "balance": case.get("balance", 0),
            "due_date": case.get("due_date", ""),
            "case_state": case.get("case_state", ""),
            "history": case.get("history", []),
            "settlement_limit_pct": case.get("settlement_limit_pct", 20),
        }
        settlement_offer = int(case.get("balance", 0) * case.get("settlement_limit_pct", 20) / 100)
        context["settlement_offer"] = settlement_offer
        context["current_message"] = case.get("current_message", "")
        
    elif bot_type == "marketing":
        context = {
            "bot_type": "marketing",
            "lead_name": case.get("lead_name", ""),
            "product": case.get("product", ""),
            "interest_rate": case.get("interest_rate", ""),
            "max_amount": case.get("max_amount", 0),
            "eligibility_score": case.get("eligibility_score", ""),
            "history": case.get("history", []),
        }
        context["current_message"] = case.get("current_message", "")
        
    else:
        raise ValueError(f"Unknown bot_type: {bot_type}")
    
    return context


def load_case(bot_type: str, case_id: str) -> Dict[str, Any]:
    """Load a specific case from the JSON data files."""
    filename = f"data/{bot_type}_cases.json"
    with open(filename, "r") as f:
        cases = json.load(f)
    
    for case in cases:
        if case.get("id") == case_id:
            return case
    
    raise ValueError(f"Case {case_id} not found in {filename}")


def list_cases(bot_type: str) -> list:
    """List all available case IDs for a bot type."""
    filename = f"data/{bot_type}_cases.json"
    with open(filename, "r") as f:
        cases = json.load(f)
    return [case["id"] for case in cases]


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python context_assembler.py <bot_type> <case_id>")
        sys.exit(1)
    
    bot_type = sys.argv[1]
    case_id = sys.argv[2]
    
    case = load_case(bot_type, case_id)
    context = assemble_context(case)
    print(json.dumps(context, indent=2))