"""What the app shows people: route names, one-paragraph explanations and the
fixed notes. The wording follows docs/annotation_guidelines.md section 3 ("The
five answers", "What the acronyms mean", "How long each route takes"), so a user
reads the same definitions the annotators labeled with.
"""
from __future__ import annotations

from dmaic_planner.schema import METHODOLOGIES

# Label codes the model predicts -> names a person reads.
DISPLAY_NAMES: dict[str, str] = {
    "JUST_DO_IT": "Just Do It",
    "KAIZEN_EVENT": "Kaizen Event",
    "DMAIC": "DMAIC",
    "DMADV": "DMADV",
    "NOT_CPI": "Not a CPI project",
}

# One line each, from the "In plain English" column of the guidelines.
TAGLINES: dict[str, str] = {
    "JUST_DO_IT": "Somebody just go fix it.",
    "KAIZEN_EVENT": "Get the right people in a room for a few days.",
    "DMAIC": "Measure before you fix.",
    "DMADV": "Design something that does not exist yet.",
    "NOT_CPI": "This is not a process-improvement problem.",
}

EXPLANATIONS: dict[str, str] = {
    "JUST_DO_IT": (
        "Just Do It means the fix is obvious enough that any structured method would be "
        "overhead. The narrative says both what is wrong and what would fix it, the fix "
        "touches one step or one team, and it sounds like hours or a couple of days of "
        "work. Whoever owns that step makes the change, then checks that it worked."
    ),
    "KAIZEN_EVENT": (
        "A Kaizen Event (from the Japanese kaizen, \"change for the better\") puts the "
        "people who do the work in a room for a few days to redesign their own workflow. "
        "It fits flow problems: work waiting, being handed back and forth, duplicated "
        "effort, a clumsy layout or too many approvals, where the rough cause is already "
        "understood. Expect a 2 to 5 day workshop with a facilitator, about two weeks of "
        "preparation and a few weeks of follow-up, ending in a redesigned flow everyone "
        "has agreed to."
    ),
    "DMAIC": (
        "DMAIC stands for Define, Measure, Analyze, Improve, Control. It is the standard "
        "improvement cycle for a process that exists but produces bad results (errors, "
        "delays, cost or wide variation) when nobody knows why. The Measure and Analyze "
        "steps are the point: collect data to find the cause before changing anything. "
        "A trained lead and a small team usually take about four months (commonly three "
        "to six) and finish with the proven cause, the fix and a plan to keep it fixed."
    ),
    "DMADV": (
        "DMADV stands for Define, Measure, Analyze, Design, Verify. It starts like DMAIC "
        "but ends by designing something new instead of repairing something old. It fits "
        "when there is no process today, when a brand-new capability is being asked for, "
        "or when the current process could never meet a new requirement even if every "
        "step went right. A design team, working with the people the process serves, "
        "usually takes about five months or longer."
    ),
    "NOT_CPI": (
        "Not a CPI project means this is not continuous process improvement (CPI) work. "
        "The request is really for money, staff, a policy decision, a purchase or "
        "compliance with a law, with no process problem inside it. It belongs with "
        "managers or budget owners, who make a decision: fund it, staff it or approve it. "
        "If a real process problem turns up later, send it back through intake."
    ),
}

# The public copy of this project on GitHub, as owner/name. tools/export_public.py builds
# that copy and reads this line, so the app's link and every link in the exported
# repository change together: rename the repository here, then export again.
PUBLIC_REPO = "jeraddunne/dmaic-planner"
PUBLIC_REPO_URL = f"https://github.com/{PUBLIC_REPO}"
USER_GUIDE_URL = f"{PUBLIC_REPO_URL}#limitations"

CONFIDENCE_NOTE = (
    "**How to read this.** The five percentages are the model's scores, shown exactly as "
    "it computed them; they add up to 100%. They say which route the wording of your "
    "narrative most resembles, not the chance that a route is correct. The model learned "
    "from only 60 labeled public narratives, and on a dataset this small its top choice "
    "is often wrong. Use the top two routes as a short list: read both explanations and "
    "decide with your process-improvement lead. The label above the scores, and the "
    "cross-validation figures under it, come from the model's own testing and say how far "
    "to trust its top choice. Where the model goes wrong, and why: "
    f"[Limitations in the user guide]({USER_GUIDE_URL})."
)

NO_TIERS_NOTE = (
    "This model has no calibrated confidence labels, so only the raw percentages are shown."
)

DISCLAIMER = (
    "Decision support only, not a substitute for a process-improvement lead. Trained on "
    "60 public process-problem narratives, so it can be wrong in ways those narratives "
    "did not cover. Do not paste personal, medical, classified or otherwise sensitive "
    "information; describe the process, not the people."
)

PLACEHOLDER_BANNER = (
    "**PLACEHOLDER MODEL.** These predictions come from the project's keyword rules "
    "(rules/methodology_rules.yaml), not from the trained model. This build exists to "
    "test the app and its deployment; the chosen model replaces it before the "
    "presentations."
)

TOOLS_NOTE = (
    "Starter checklist from the project's rule tables (rules/tool_map.yaml), by phase "
    "of the predicted route. It is the same for every narrative with this route, plus "
    "any waste-specific tools the keyword rules spot in your text. It is not generated "
    "by the model."
)
