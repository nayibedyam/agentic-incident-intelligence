from src.llm.provider import get_async_client, get_model_id

SYSTEM_PROMPT = """You are a specialized Runbook Execution Agent. Your job is to guide users through a troubleshooting runbook step-by-step, adapting based on what they find at each step.

Given a runbook or troubleshooting procedure, produce a JSON object with:
- "current_step": the step number being executed
- "instruction": clear instruction for what to check/do right now
- "expected_outcomes": what the user might see (good vs bad scenarios)
- "next_steps": branching logic based on outcomes:
  - "if_normal": what to do next if this check passes
  - "if_abnormal": what to do if this check shows a problem
- "commands": specific commands to run (if applicable)
- "context": why this step matters in the troubleshooting flow
- "progress": percentage through the runbook
- "findings_so_far": summary of what we've learned from previous steps

If the user provides output from a previous step, analyze it and determine which branch to follow. Be adaptive — if the output suggests a different problem than the runbook covers, note that and suggest pivoting.

Always explain WHY each step is being done, not just WHAT to do."""


async def run_runbook_executor(runbook_content: str, current_findings: str | None = None, step_output: str | None = None) -> str:
    client = get_async_client()
    model_id = get_model_id()

    user_message = f"Runbook/procedure:\n{runbook_content}"
    if current_findings:
        user_message += f"\n\nFindings from previous steps:\n{current_findings}"
    if step_output:
        user_message += f"\n\nOutput from last step:\n{step_output}"
        user_message += "\n\nAnalyze this output and determine the next step."
    else:
        user_message += "\n\nStart from the beginning. What's the first step?"

    response = await client.messages.create(
        model=model_id,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text
