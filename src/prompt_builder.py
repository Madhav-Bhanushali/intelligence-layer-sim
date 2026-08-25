import hashlib
from pathlib import Path
from typing import Dict, Any, List


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt_file(filename: str) -> str:
    """Load a prompt file from the prompts directory."""
    filepath = PROMPTS_DIR / filename
    with open(filepath, "r") as f:
        return f.read()


def get_file_hash(filename: str) -> str:
    """Get a short hash of the file content for version tracking."""
    content = load_prompt_file(filename)
    return hashlib.md5(content.encode()).hexdigest()[:8]


def build_prompt(context: Dict[str, Any], current_message: str) -> Dict[str, Any]:
    """
    Build the full prompt for the model.
    Returns a dict with messages (Anthropic Messages API format) and prompt version info.
    """
    bot_type = context.get("bot_type", "collection")
    
    if bot_type == "collection":
        system_file = "collection_system.md"
        fewshot_file = "collection_fewshot.md"
    elif bot_type == "marketing":
        system_file = "marketing_system.md"
        fewshot_file = "marketing_fewshot.md"
    else:
        raise ValueError(f"Unknown bot_type: {bot_type}")
    
    system_prompt = load_prompt_file(system_file)
    fewshot_prompt = load_prompt_file(fewshot_file)
    
    context_str = format_context_for_prompt(context)
    
    user_content = f"{context_str}\n\nCurrent message: {current_message}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": fewshot_prompt},
        {"role": "user", "content": user_content},
    ]
    
    version_info = {
        "system_file": system_file,
        "system_version": get_file_hash(system_file),
        "fewshot_file": fewshot_file,
        "fewshot_version": get_file_hash(fewshot_file),
    }
    
    return {
        "messages": messages,
        "version_info": version_info,
    }


def format_context_for_prompt(context: Dict[str, Any]) -> str:
    """Format context as a readable string for the prompt."""
    lines = []
    for key, value in context.items():
        if key not in ["current_message", "history"]:
            lines.append(f"- {key}: {value}")
    
    if context.get("history"):
        lines.append("- history:")
        for item in context["history"]:
            lines.append(f"  - {item}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from context_assembler import assemble_context, load_case
    
    if len(sys.argv) < 3:
        print("Usage: python prompt_builder.py <bot_type> <case_id>")
        sys.exit(1)
    
    bot_type = sys.argv[1]
    case_id = sys.argv[2]
    
    case = load_case(bot_type, case_id)
    context = assemble_context(case)
    prompt = build_prompt(context, case.get("current_message", ""))
    
    print("=== VERSION INFO ===")
    for k, v in prompt["version_info"].items():
        print(f"{k}: {v}")
    print("\n=== MESSAGES ===")
    for msg in prompt["messages"]:
        print(f"\n[{msg['role']}]")
        print(msg["content"][:500] + ("..." if len(msg["content"]) > 500 else ""))