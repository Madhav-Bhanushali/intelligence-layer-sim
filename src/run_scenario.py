import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from context_assembler import assemble_context, load_case, list_cases
from prompt_builder import build_prompt
from model_router import route_message
from model_client import call_model_by_type
from output_validator import validate_output


def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_json(obj: dict, indent: int = 2):
    print(json.dumps(obj, indent=indent))


def save_trace_json(trace: dict, output_dir: Path, case_id: str):
    """Save trace as JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f"{case_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump(trace, f, indent=2, default=str)
    print(f"\nTrace saved to: {filename}")
    return filename


def save_trace_md(trace: dict, output_dir: Path, case_id: str):
    """Save trace as Markdown file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f"{case_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    with open(filename, "w") as f:
        f.write(f"# Intelligence Layer Simulation Trace\n\n")
        f.write(f"**Case ID:** {trace['case_id']}  \n")
        f.write(f"**Bot Type:** {trace['bot_type']}  \n")
        f.write(f"**Timestamp:** {datetime.now().isoformat()}  \n\n")
        
        f.write("## 1. Assembled Context\n\n")
        f.write("```json\n")
        f.write(json.dumps(trace['context'], indent=2))
        f.write("\n```\n\n")
        
        f.write("## 2. Router Decision\n\n")
        f.write(f"**Classification:** {trace['router']['classification']}  \n")
        f.write(f"**Reason:** {trace['router']['reason']}  \n\n")
        
        f.write("## 3. Prompt Version Info\n\n")
        for k, v in trace['prompt_version'].items():
            f.write(f"- **{k}:** {v}  \n")
        f.write("\n")
        
        f.write("## 4. Model Called\n\n")
        mr = trace['model_result']
        f.write(f"**Model:** {mr['model']} ({mr.get('provider', 'unknown')})  \n")
        f.write(f"**Success:** {mr['success']}  \n")
        if mr['success']:
            f.write(f"**Usage:** {mr.get('usage', {})}  \n")
        else:
            f.write(f"**Error:** {mr.get('error', 'Unknown')}  \n")
        f.write("\n")
        
        f.write("## 5. Raw Model Output\n\n")
        if mr['success']:
            f.write("```\n")
            f.write(mr['output'])
            f.write("\n```\n\n")
        else:
            f.write(f"*Model call failed: {mr.get('error', 'Unknown error')}*\n\n")
        
        f.write("## 6. Validator Result\n\n")
        vr = trace['validator_result']
        f.write(f"**Passed:** {vr['passed']}  \n")
        f.write(f"**Reason:** {vr['reason']}  \n")
        if 'details' in vr:
            f.write("\n**Details:**\n\n")
            for check_name, check_result in vr['details'].items():
                f.write(f"- **{check_name}:** {check_result['passed']} — {check_result['reason']}  \n")
        f.write("\n")
        
        f.write("## 7. Final Output\n\n")
        if trace['final_output']:
            f.write("```\n")
            f.write(trace['final_output'])
            f.write("\n```\n")
        else:
            f.write(f"**BLOCKED** — validator failed: {vr.get('reason', 'Unknown validation failure')}\n")
    
    print(f"\nTrace saved to: {filename}")
    return filename


def run_scenario(bot_type: str, case_id: str, save_json: bool = False, save_md: bool = False, output_dir: str = "traces") -> Dict[str, Any]:
    """Run a single scenario end-to-end and return the full trace."""
    
    case = load_case(bot_type, case_id)
    context = assemble_context(case)
    current_message = case.get("current_message", "")
    
    print_section("1. ASSEMBLED CONTEXT")
    print_json(context)
    
    classification, reason = route_message(bot_type, current_message)
    print_section("2. ROUTER DECISION")
    print(f"Classification: {classification}")
    print(f"Reason: {reason}")
    
    prompt = build_prompt(context, current_message)
    print_section("3. PROMPT USED")
    print(f"System file: {prompt['version_info']['system_file']} (v{prompt['version_info']['system_version']})")
    print(f"Few-shot file: {prompt['version_info']['fewshot_file']} (v{prompt['version_info']['fewshot_version']})")
    print("\n--- Messages ---")
    for i, msg in enumerate(prompt["messages"]):
        print(f"\n[{msg['role']}] (truncated)")
        content = msg["content"]
        print(content[:800] + ("..." if len(content) > 800 else ""))
    
    print_section("4. MODEL CALLED")
    print(f"Routing to: {classification} model")
    
    model_result = call_model_by_type(prompt["messages"], classification)
    
    print_section("5. RAW MODEL OUTPUT")
    print(f"Model: {model_result['model']}")
    print(f"Success: {model_result['success']}")
    if model_result['success']:
        try:
            print(model_result['output'])
        except UnicodeEncodeError:
            print(model_result['output'].encode('ascii', 'replace').decode('ascii'))
        if 'usage' in model_result:
            print(f"\nUsage: {model_result['usage']}")
    else:
        print(f"Error: {model_result.get('error')}")
    
    print_section("6. VALIDATOR RESULT")
    if model_result['success']:
        validator_result = validate_output(model_result['output'], context)
        print_json(validator_result)
    else:
        validator_result = {"passed": False, "reason": "Model call failed"}
        print_json(validator_result)
    
    print_section("7. FINAL OUTPUT")
    if model_result['success'] and validator_result['passed']:
        try:
            print(model_result['output'])
        except UnicodeEncodeError:
            print(model_result['output'].encode('ascii', 'replace').decode('ascii'))
    else:
        reason = validator_result.get('reason', 'Unknown validation failure')
        try:
            print(f"BLOCKED — validator failed: {reason}")
        except UnicodeEncodeError:
            pass
    
    trace = {
        "case_id": case_id,
        "bot_type": bot_type,
        "context": context,
        "router": {"classification": classification, "reason": reason},
        "prompt_version": prompt["version_info"],
        "model_result": model_result,
        "validator_result": validator_result,
        "final_output": model_result['output'] if model_result['success'] and validator_result['passed'] else None,
    }
    
    if save_json:
        save_trace_json(trace, Path(output_dir), case_id)
    
    if save_md:
        save_trace_md(trace, Path(output_dir), case_id)
    
    return trace


def main():
    parser = argparse.ArgumentParser(
        description="Run intelligence layer simulation scenario"
    )
    parser.add_argument("--bot", choices=["collection", "marketing"], required=True, help="Bot type")
    parser.add_argument("--case", help="Case ID to run")
    parser.add_argument("--list", action="store_true", help="List available cases for the bot type")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (no API calls)")
    parser.add_argument("--save-json", action="store_true", help="Save trace as JSON file")
    parser.add_argument("--save-md", action="store_true", help="Save trace as Markdown file")
    parser.add_argument("--output-dir", default="traces", help="Output directory for trace files")
    
    args = parser.parse_args()
    
    if args.mock:
        import os
        os.environ["MOCK_MODE"] = "true"
    
    if args.list:
        cases = list_cases(args.bot)
        print(f"Available {args.bot} cases:")
        for case_id in cases:
            print(f"  - {case_id}")
        return
    
    if not args.case:
        parser.error("--case is required when not using --list")
    
    try:
        trace = run_scenario(args.bot, args.case, args.save_json, args.save_md, args.output_dir)
        print("\n" + "=" * 60)
        print("SCENARIO COMPLETE")
        print("=" * 60)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()