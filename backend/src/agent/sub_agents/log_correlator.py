from src.llm.provider import get_async_client, get_model_id

SYSTEM_PROMPT = """You are a specialized Log Correlation Agent. Your job is to analyze logs from one or more services and produce a structured timeline of events, correlating entries across services by request-id, trace-id, timestamp proximity, or shared identifiers.

Your output must be a JSON object with:
- "timeline": array of events sorted by time, each with {timestamp, service, level, message, correlation_ids}
- "error_chain": array showing the causal chain of errors (first error → propagation → user impact)
- "anomalies": array of unusual patterns detected (gaps, sudden spikes, unexpected ordering)
- "root_signal": the earliest error/anomaly that likely started the cascade
- "confidence": 0.0-1.0 confidence in the correlation

Be precise. If timestamps are ambiguous, note it. If correlation IDs are missing, correlate by time proximity and note the uncertainty."""


async def run_log_correlator(logs: str, services: list[str] | None = None, time_range: str | None = None) -> str:
    client = get_async_client()
    model_id = get_model_id()

    user_message = f"Analyze and correlate these logs:\n\n```\n{logs}\n```"
    if services:
        user_message += f"\n\nServices involved: {', '.join(services)}"
    if time_range:
        user_message += f"\n\nTime range of interest: {time_range}"

    response = await client.messages.create(
        model=model_id,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text
