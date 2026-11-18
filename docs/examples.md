# Illustrative workflow examples

These are **test-fixture examples** for understanding the output format. They use fictional values and `example.com` links; they are not current intelligence, validated reporting, or evidence that a live provider was reachable.

## Research report fixture

**Request:** Research a fictional research milestone.

**Evidence fixtures:**

- **Reuters** — “Researchers report a quantum computing milestone” — `https://example.com/reuters` — fixture snippet: “A team reported progress on error correction.”
- **Associated Press** — “Researchers report quantum computing milestone” — `https://example.org/ap` — fixture snippet: “The team reported a similar development.”

**Illustrative synthesis:** Researchers reported a quantum computing milestone. Two distinct publishers have similar fixture headlines, so the example can describe cross-source agreement while noting that the underlying claims remain unverified from snippets alone. In a real response, FRIDAY should retain source links and clearly state when article text was not retrieved.

## Intelligence briefing fixture

**Request:** Prepare a briefing on a fictionalized region fixture.

**Fixture inputs:** World risk index `68.5`, active conflicts `2`, economic stability `55.5`, and a region indicator marked live with timestamp `2026-11-17T10:00:00+00:00`. Example event headlines and links use placeholder `example.com` domains. A separate region fixture is present to verify region filtering.

**Illustrative output shape:**

1. **Region and risk overview** — identify the requested region and report only matching fixture indicators.
2. **Recent reporting** — summarize dated headlines and preserve source names and links.
3. **Evidence and uncertainty** — distinguish live-source metadata from snippets, identify missing article text, and describe contradictions or confidence limits.
4. **Potential implications (analysis, not prediction)** — label analysis separately from observed source data.

The corresponding automated fixture is in `backend/tests/test_intelligence_agent.py`; its numbers and events are synthetic test inputs, not current measurements.

## Execution trace fixture

```json
{
  "trace_id": "trc-example",
  "user_prompt": "Prepare a briefing on a fictional region",
  "intent": {
    "intent": "world_intelligence",
    "requires_tools": true,
    "complexity": "multi_step",
    "confidence": 1.0,
    "entities": {}
  },
  "agent_used": "intelligence_agent",
  "steps_executed": [
    {
      "step_number": 1,
      "description": "Retrieve telemetry",
      "tool_name": "world_monitor_telemetry",
      "status": "completed",
      "duration_seconds": 0.1
    },
    {
      "step_number": 2,
      "description": "Search supporting reports",
      "tool_name": "web_search",
      "status": "completed",
      "duration_seconds": 0.2
    }
  ],
  "model_used": "local-model",
  "model_latency_seconds": 0.3,
  "token_count": null,
  "sources_used": ["World Monitor", "Example publisher"],
  "warnings": [],
  "total_duration_seconds": 0.6,
  "created_at": "2026-01-01T00:00:00+00:00"
}
```

This compact trace is illustrative; the application may include additional plan, tool-input, observation, and timing fields. User prompts and trace details can be retained only when the separate execution-history option is enabled.
