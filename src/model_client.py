import os
import json
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("MODEL_PROVIDER", "anthropic").lower()


def get_provider() -> str:
    """Get the current provider (reads env var at call time)."""
    return os.getenv("MODEL_PROVIDER", "anthropic").lower()


def is_mock_mode() -> bool:
    """Check if mock mode is enabled (reads env var at call time)."""
    return os.getenv("MOCK_MODE", "false").lower() == "true"

# Anthropic models
ANTHROPIC_SMALL = "claude-haiku-4-5-20251001"
ANTHROPIC_LARGE = "claude-sonnet-5"

# Gemini models
GEMINI_SMALL = "gemini-1.5-flash"
GEMINI_LARGE = "gemini-1.5-pro"

# Groq models
GROQ_SMALL = "openai/gpt-oss-20b"
GROQ_LARGE = "openai/gpt-oss-120b"

# Mock models
MOCK_SMALL = "mock-haiku"
MOCK_LARGE = "mock-sonnet"

_anthropic_client: Optional[Any] = None
_gemini_client: Optional[Any] = None
_groq_client: Optional[Any] = None


def generate_mock_response(
    messages: List[Dict[str, str]],
    classification: str,
    bot_type: str,
    context: Dict[str, Any]
) -> str:
    """Generate a realistic mock response based on context and classification."""
    
    current_message = ""
    for msg in messages:
        if msg["role"] == "user" and "Current message:" in msg["content"]:
            current_message = msg["content"].split("Current message:")[-1].strip()
            break
    
    if bot_type == "collection":
        borrower_name = context.get("borrower_name", "the borrower")
        balance = context.get("balance", 0)
        settlement_offer = context.get("settlement_offer", 0)
        case_state = context.get("case_state", "")
        
        if classification == "routine":
            if "due" in current_message.lower() or "when" in current_message.lower():
                return f"Hello {borrower_name}. Your payment of Rs.{balance:,} was due. Please make the payment at your earliest convenience to avoid any late fees."
            elif "confirm" in current_message.lower() or "paid" in current_message.lower():
                return f"Yes, {borrower_name}. We received your payment of Rs.{balance:,}. Your account is now up to date. Thank you for your payment."
            else:
                return f"Hello {borrower_name}. Your current balance is Rs.{balance:,}. Please let us know if you have any questions."
        
        else:  # complex
            if "half" in current_message.lower() or "partial" in current_message.lower():
                return f"Thank you for reaching out, {borrower_name}. I understand you'd like to discuss a partial payment. Your current balance is Rs.{balance:,}. Based on our policy, we can accept a settlement of up to Rs.{settlement_offer:,} as a one-time offer, or we can discuss a repayment plan. Which option would work better for you?"
            elif "dispute" in current_message.lower() or "mistake" in current_message.lower() or "never took" in current_message.lower():
                return f"I understand your concern, {borrower_name}. According to our records, there is an outstanding balance of Rs.{balance:,} on your account. If you believe this is an error, I can escalate this to our disputes team for a full review. Would you like me to do that?"
            elif "settlement" in current_message.lower() or "offer" in current_message.lower():
                return f"I appreciate your offer, {borrower_name}. Your current balance is Rs.{balance:,}. The maximum settlement we can offer is Rs.{settlement_offer:,} as a one-time payment. If you can pay Rs.{settlement_offer:,}, we can close this account. Please let me know if this works for you."
            elif "repayment plan" in current_message.lower() or "month" in current_message.lower():
                return f"I understand your situation, {borrower_name}. Your balance is Rs.{balance:,}. We can discuss a repayment plan. Please contact our team to set up a plan that works for you."
            else:
                return f"Hello {borrower_name}. Your balance is Rs.{balance:,}. How can I assist you today?"
    
    else:  # marketing
        lead_name = context.get("lead_name", "the lead")
        product = context.get("product", "loan")
        interest_rate = context.get("interest_rate", "")
        max_amount = context.get("max_amount", 0)
        eligibility_score = context.get("eligibility_score", "")
        
        if classification == "routine":
            if "eligible" in current_message.lower():
                return f"Hi {lead_name}! Based on your profile, you have a {eligibility_score} eligibility score for our {product}. The interest rate is {interest_rate} with a maximum amount of Rs.{max_amount:,}. You're pre-qualified to apply."
            elif "offer" in current_message.lower() or "notification" in current_message.lower():
                return f"Hello {lead_name}! You've been pre-screened for a {product} offer with an interest rate of {interest_rate} and a maximum amount of Rs.{max_amount:,}. Your current eligibility score is {eligibility_score}. Would you like to proceed with a formal application?"
            else:
                return f"Hi {lead_name}! We're offering a {product} with an interest rate of {interest_rate} and a maximum loan amount of Rs.{max_amount:,}. Based on your profile, your eligibility score is {eligibility_score}. Would you like to know more?"
        
        else:  # complex
            if "custom" in current_message.lower() or "tailored" in current_message.lower() or "profile" in current_message.lower():
                return f"Thank you for sharing that, {lead_name}. With your profile and {eligibility_score} eligibility score, you qualify for our {product} at {interest_rate} interest with up to Rs.{max_amount:,}. Given your situation, you may benefit from our quick disbursal process. Would you like me to walk you through the next steps?"
            elif "term" in current_message.lower() or "fee" in current_message.lower() or "repayment" in current_message.lower():
                return f"The {product} has an interest rate of {interest_rate} with a maximum amount of Rs.{max_amount:,}. Regarding repayment terms, we offer flexible options. I don't have the exact processing fee in my current data — I'd recommend checking the official product brochure for the complete fee structure."
            elif "business" in current_message.lower() or "machinery" in current_message.lower():
                return f"For your manufacturing unit, the {product} offers {interest_rate} interest with up to Rs.{max_amount:,}. This can be used for machinery purchases. Given your business profile and {eligibility_score} eligibility, you may qualify for favorable terms. Would you like to discuss the application process?"
            else:
                return f"Hello {lead_name}! Our {product} has an interest rate of {interest_rate} and maximum amount of Rs.{max_amount:,}. How can I help you further?"
    
    return "Thank you for your message. How can I assist you?"


def call_mock(
    messages: List[Dict[str, str]],
    model: str,
    max_tokens: int = 1024,
    temperature: float = 0.3
) -> Dict[str, Any]:
    """Generate a mock response for testing without API calls."""
    try:
        # Extract bot_type from the system message
        system_content = ""
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
                break
        
        bot_type = "collection"
        if "marketing" in system_content.lower() or "loan marketing" in system_content.lower():
            bot_type = "marketing"
        
        # Determine classification from model name
        classification = "routine" if "small" in model.lower() or "flash" in model.lower() or "haiku" in model.lower() else "complex"
        
        # Extract context from the last user message (contains formatted context)
        context = {}
        for msg in reversed(messages):
            if msg["role"] == "user" and "bot_type:" in msg["content"]:
                lines = msg["content"].split("\n")
                for line in lines:
                    stripped = line.strip()
                    if ":" in stripped:
                        # Handle lines starting with "- " or just key: value
                        key_part, val = stripped.split(":", 1)
                        key = key_part.lstrip("- ").strip()
                        val = val.strip()
                        try:
                            context[key] = int(val.replace(",", ""))
                        except ValueError:
                            try:
                                context[key] = float(val.replace(",", ""))
                            except ValueError:
                                context[key] = val
                break
        
        # If we couldn't extract context, use defaults based on bot_type
        if not context:
            if bot_type == "collection":
                context = {"borrower_name": "Customer", "balance": 25000, "settlement_offer": 5000}
            else:
                context = {"lead_name": "Lead", "product": "Personal Loan", "interest_rate": "11.5%", "max_amount": 500000, "eligibility_score": "high"}
        
        output = generate_mock_response(messages, classification, bot_type, context)
        
        return {
            "success": True,
            "output": output,
            "model": model,
            "provider": "mock",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "model": model,
            "provider": "mock",
            "error": str(e),
        }


def get_anthropic_client():
    """Get or create the Anthropic client."""
    global _anthropic_client
    if _anthropic_client is None:
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ValueError("anthropic package not installed. Run: pip install anthropic")
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        _anthropic_client = Anthropic(api_key=api_key)
    return _anthropic_client


def get_gemini_client():
    """Get or create the Gemini client."""
    global _gemini_client
    if _gemini_client is None:
        try:
            import google.generativeai as genai
        except ImportError:
            raise ValueError("google-generativeai package not installed. Run: pip install google-generativeai")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        _gemini_client = genai
    return _gemini_client


def get_groq_client():
    """Get or create the Groq client."""
    global _groq_client
    if _groq_client is None:
        try:
            from groq import Groq
        except ImportError:
            raise ValueError("groq package not installed. Run: pip install groq")
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def call_anthropic(
    messages: List[Dict[str, str]],
    model: str,
    max_tokens: int = 1024,
    temperature: float = 0.3
) -> Dict[str, Any]:
    """Call the Anthropic Messages API."""
    try:
        client = get_anthropic_client()
        
        system_message = None
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                user_messages.append({"role": msg["role"], "content": msg["content"]})
        
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_message,
            messages=user_messages,
        )
        
        output = ""
        for block in response.content:
            if block.type == "text":
                output += block.text
        
        return {
            "success": True,
            "output": output,
            "model": model,
            "provider": "anthropic",
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "model": model,
            "provider": "anthropic",
            "error": str(e),
        }


def call_gemini(
    messages: List[Dict[str, str]],
    model: str,
    max_tokens: int = 1024,
    temperature: float = 0.3
) -> Dict[str, Any]:
    """Call the Gemini API."""
    try:
        genai = get_gemini_client()
        
        system_message = None
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                user_messages.append({"role": msg["role"], "content": msg["content"]})
        
        gemini_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_message if system_message else None,
        )
        
        chat = gemini_model.start_chat(history=[])
        
        response = chat.send_message(
            user_messages[-1]["content"] if user_messages else "",
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        
        output = response.text if response.text else ""
        
        return {
            "success": True,
            "output": output,
            "model": model,
            "provider": "gemini",
            "usage": {
                "input_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0) if hasattr(response, 'usage_metadata') else 0,
                "output_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0) if hasattr(response, 'usage_metadata') else 0,
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "model": model,
            "provider": "gemini",
            "error": str(e),
        }


def call_groq(
    messages: List[Dict[str, str]],
    model: str,
    max_tokens: int = 1024,
    temperature: float = 0.3
) -> Dict[str, Any]:
    """Call the Groq API (OpenAI-compatible)."""
    try:
        client = get_groq_client()
        
        system_message = None
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                user_messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Groq uses OpenAI-compatible format
        api_messages = []
        if system_message:
            api_messages.append({"role": "system", "content": system_message})
        api_messages.extend(user_messages)
        
        response = client.chat.completions.create(
            model=model,
            messages=api_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        output = response.choices[0].message.content if response.choices else ""
        
        return {
            "success": True,
            "output": output,
            "model": model,
            "provider": "groq",
            "usage": {
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "model": model,
            "provider": "groq",
            "error": str(e),
        }


def call_model(
    messages: List[Dict[str, str]],
    model: str,
    max_tokens: int = 1024,
    temperature: float = 0.3
) -> Dict[str, Any]:
    """Call the appropriate provider based on MODEL_PROVIDER env var."""
    if is_mock_mode():
        return call_mock(messages, model, max_tokens, temperature)
    provider = get_provider()
    if provider == "gemini":
        return call_gemini(messages, model, max_tokens, temperature)
    elif provider == "groq":
        return call_groq(messages, model, max_tokens, temperature)
    else:
        return call_anthropic(messages, model, max_tokens, temperature)


def get_small_model() -> str:
    """Get the small model name for the current provider."""
    if is_mock_mode():
        return MOCK_SMALL
    provider = get_provider()
    if provider == "groq":
        return GROQ_SMALL
    if provider == "gemini":
        return GEMINI_SMALL
    return ANTHROPIC_SMALL


def get_large_model() -> str:
    """Get the large model name for the current provider."""
    if is_mock_mode():
        return MOCK_LARGE
    provider = get_provider()
    if provider == "groq":
        return GROQ_LARGE
    if provider == "gemini":
        return GEMINI_LARGE
    return ANTHROPIC_LARGE


def call_small_model(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Call the small/cheap model for routine cases."""
    return call_model(messages, get_small_model())


def call_large_model(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Call the large/capable model for complex cases."""
    return call_model(messages, get_large_model())


def call_model_by_type(
    messages: List[Dict[str, str]],
    classification: str
) -> Dict[str, Any]:
    """Route to the appropriate model based on classification."""
    if classification == "routine":
        return call_small_model(messages)
    elif classification == "complex":
        return call_large_model(messages)
    else:
        raise ValueError(f"Unknown classification: {classification}")


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from prompt_builder import build_prompt
    from context_assembler import assemble_context, load_case
    from model_router import route_message
    
    if len(sys.argv) < 3:
        print("Usage: python model_client.py <bot_type> <case_id>")
        sys.exit(1)
    
    bot_type = sys.argv[1]
    case_id = sys.argv[2]
    
    case = load_case(bot_type, case_id)
    context = assemble_context(case)
    
    classification, reason = route_message(bot_type, case.get("current_message", ""))
    print(f"Router: {classification} ({reason})")
    print(f"Provider: {PROVIDER}")
    
    prompt = build_prompt(context, case.get("current_message", ""))
    
    result = call_model_by_type(prompt["messages"], classification)
    
    print(f"Model: {result['model']} ({result.get('provider', 'unknown')})")
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Output: {result['output']}")
        print(f"Usage: {result.get('usage', {})}")
    else:
        print(f"Error: {result.get('error')}")