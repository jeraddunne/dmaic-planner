"""DMAIC Planner web app: paste a process-problem narrative, get an improvement
route, its confidence, a plain-language explanation and a starter tools checklist.

    python -m app.main                      # from the repository root
    open http://127.0.0.1:7860

Environment:
  PORT         port to listen on (default 7860; Cloud Run sets it)
  HOST         interface to bind (default 0.0.0.0)
  DMAIC_MODEL  which model backend to load (see app/predictor.py)

API: one endpoint, /predict, takes the narrative as a string and returns a JSON
object (see "Use via API" at the bottom of the page, and app/README.md).
"""
from __future__ import annotations

import logging
import os

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import gradio as gr  # noqa: E402

from app.examples import EXAMPLES  # noqa: E402
from app.labels import (  # noqa: E402
    CONFIDENCE_NOTE, DISCLAIMER, DISPLAY_NAMES, EXPLANATIONS, PLACEHOLDER_BANNER, TAGLINES, TOOLS_NOTE,
)
from app.service import PlannerService  # noqa: E402
from app.validation import MAX_CHARS, MIN_WORDS  # noqa: E402

log = logging.getLogger("app")

INTRO = (
    "Describe **one process problem** in a few sentences: what happens, where, how often, "
    "what it costs, and whether anyone knows why. The app recommends one of five "
    "improvement routes, shows its confidence in each, explains the route in plain "
    "language and lists starter tools for it."
)

CSS = """
.callout { border-left: 4px solid #d97706; padding-left: 12px; }
.small { font-size: 0.9em; opacity: 0.85; }
"""


def _ms(value: float) -> str:
    return f"{value:.1f}" if value < 100 else f"{value:.0f}"


def render_tools(tools: dict[str, list[str]]) -> str:
    lines = ["#### Starter tools checklist", f"<span class='small'>{TOOLS_NOTE}</span>", ""]
    for phase, items in tools.items():
        lines.append(f"**{phase}**")
        lines += [f"- ☐ {item}" for item in items]
        lines.append("")
    return "\n".join(lines)


def render(result: dict) -> tuple:
    """Service result -> (headline, confidences, explanation, tools, footer)."""
    footer = f"Model version: `{result['model_version']}` · Server time for this request: {_ms(result['latency_ms'])} ms"
    if not result["ok"]:
        return (f"<div class='callout'><b>Please check your input.</b> {result['error']}</div>",
                None, "", "", footer)
    runner = result["runner_up"]
    lines = [f"### Recommended route: {result['route']} ({result['confidence']:.0%})"]
    if result["tier"]:
        lines.append(f"**{result['tier']}**")
        evidence = []
        if result["tier_oof_accuracy"] is not None:
            evidence.append(f"the top route was right {result['tier_oof_accuracy']:.0%} of the time "
                            "for predictions like this")
        if result["top2_oof_accuracy"] is not None:
            evidence.append(f"the right route was among the top two {result['top2_oof_accuracy']:.0%} of the time")
        if evidence:
            lines.append(f"<span class='small'>In cross-validation, {' and '.join(evidence)}.</span>")
    lines.append(f"Top two: **{result['route']} {result['confidence']:.0%}** · "
                 f"**{runner['route']} {runner['confidence']:.0%}**")
    if result["tier_note"]:
        lines.append(f"<span class='small'>{result['tier_note']}</span>")
    if result["note"]:
        lines.append(f"<div class='callout'><b>Note:</b> {result['note']}</div>")
    headline = "\n\n".join(lines)
    explanation = (f"#### What {result['route']} means (top choice)\n*{result['tagline']}* {result['explanation']}\n\n"
                   f"#### What {runner['route']} means (runner-up)\n*{runner['tagline']}* {runner['explanation']}")
    footer += f" (model {_ms(result['model_ms'])} ms)"
    return headline, result["confidences"], explanation, render_tools(result["tools"]), footer


def build_demo(service: PlannerService) -> gr.Blocks:
    def recommend(narrative):
        return render(service.classify(narrative))

    def predict(narrative: str) -> dict:
        """Route one process-problem narrative (a string of at least 15 words) to an
        improvement methodology. Returns a JSON object: ok, route, confidence,
        confidences (all five routes), explanation, tools, note, model_version,
        latency_ms. On bad input ok is false and error says what to fix."""
        return service.classify(narrative)

    with gr.Blocks(title="DMAIC Planner") as demo:
        gr.Markdown("# DMAIC Planner\nWhich process-improvement route fits this problem?")
        gr.Markdown(INTRO)
        if service.predictor.is_placeholder:
            gr.Markdown(f"<div class='callout'>{PLACEHOLDER_BANNER}</div>")

        with gr.Row():
            with gr.Column(scale=1):
                narrative = gr.Textbox(
                    label="Process-problem narrative",
                    info=f"Plain text, at least {MIN_WORDS} words. Up to {MAX_CHARS:,} characters are used; "
                         "longer text is cut, with a note.",
                    placeholder="Example: Travel vouchers sit in the approver's inbox for two to three weeks, "
                                "and about a third come back for missing receipts...",
                    lines=10, max_lines=20,
                )
                with gr.Row():
                    clear = gr.Button("Clear")
                    submit = gr.Button("Recommend a route", variant="primary")
                gr.Examples(
                    examples=[[text] for _, text in EXAMPLES],
                    example_labels=[title for title, _ in EXAMPLES],
                    inputs=narrative,
                    label="Illustrative examples (written for this demo, not taken from the dataset). Click one, then Recommend.",
                )
            with gr.Column(scale=1):
                headline = gr.Markdown("### Your result will appear here")
                confidences = gr.Label(label="Confidence for all five routes", num_top_classes=5,
                                       show_heading=False)
                gr.Markdown(f"<span class='small'>{CONFIDENCE_NOTE}</span>")
                explanation = gr.Markdown()
                tools = gr.Markdown()

        footer = gr.Markdown(f"Model version: `{service.model_version}`")
        with gr.Accordion("What the five routes mean", open=False):
            gr.Markdown("\n\n".join(f"**{DISPLAY_NAMES[c]}**: *{TAGLINES[c]}* {EXPLANATIONS[c]}"
                                    for c in DISPLAY_NAMES))
        gr.Markdown(f"<span class='small'><b>Disclaimer.</b> {DISCLAIMER}</span>")

        outputs = [headline, confidences, explanation, tools, footer]
        submit.click(recommend, inputs=narrative, outputs=outputs, api_visibility="private")
        clear.click(lambda: ("", "### Your result will appear here", None, "", "",
                             f"Model version: `{service.model_version}`"),
                    outputs=[narrative, *outputs], api_visibility="private")
        gr.api(predict, api_name="predict")
    return demo


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    service = PlannerService()
    service.warm_up()
    log.info("model ready: %s", service.model_version)
    # Serve through uvicorn instead of Blocks.launch(). launch() checks that it
    # can reach its own localhost URL and exits if it can't; on Cloud Run the CPU
    # is throttled outside requests once the port opens, so that self-check
    # times out and the container dies (503). Mounting skips the self-check and
    # serves the same UI and /predict API.
    import fastapi
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "7860"))
    app = gr.mount_gradio_app(fastapi.FastAPI(), build_demo(service), path="/",
                              css=CSS, show_error=False)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
