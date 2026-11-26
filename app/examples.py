"""Example inputs shown in the app. Written for this demo: illustrative only, not
items from the dataset or the Kaggle test set, and no real people or places.
Each one was written with a route in mind, but the app shows only the text, so a
visitor sees what the model does rather than what we hoped it would do.
"""
from __future__ import annotations

# (button label, narrative)
EXAMPLES: list[tuple[str, str]] = [
    ("Approvals bottleneck", (
        "Purchase requests under $5,000 pass through five approvals: the requester's "
        "supervisor, the budget analyst, the division chief, contracting and finance. "
        "Each approval waits in an inbox for one to three days, and about a third of "
        "requests bounce back at least once for a missing quote. Everyone agrees the two "
        "middle approvals add nothing for small purchases. We want the people who handle "
        "these requests to spend a few days redesigning the flow."
    )),
    ("Invoice errors, cause unknown", (
        "About 18 percent of the monthly invoices our billing team sends out have to be "
        "corrected and reissued. The error rate is much higher at two of our five "
        "regional offices, and it jumped last spring, but nobody can say why. We have two "
        "years of invoice and correction records in the billing system. Leadership wants "
        "to know what is driving the errors before anything changes."
    )),
    ("No complaint process yet", (
        "Starting next fiscal year, a new state rule requires every client complaint to "
        "be acknowledged within one business day and resolved within 30 days. Today "
        "complaints arrive by phone, email and paper forms, each department handles them "
        "its own way, and there is no shared log or owner. We need to design a complaint "
        "process that can meet the new requirement."
    )),
    ("Misrouted form", (
        "The online repair request form still sends laptop problems to the old help desk "
        "mailbox, which nobody has watched since the service desk moved in March. Those "
        "requests sit unanswered until the person calls. Change the form so laptop "
        "requests go to the new service desk queue."
    )),
    ("Budget request", (
        "Our team needs funding for two additional analyst positions and a license for a "
        "new reporting tool before the next budget cycle closes. The current analysts are "
        "fully booked through the end of the year. We are asking leadership to approve the "
        "headcount and the purchase."
    )),
]
