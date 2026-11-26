# Annotation Guidelines — DMAIC Planner dataset

> **Public copy.** This document comes from the project's private course repository, which
> holds the full project history and is available to the ARI 410/510 instructor on request.
> Commands such as `python tasks.py ...`, issue and pull-request numbers, and files that are
> not in this repository refer to that private repository.

**Version 1.0** · ARI 410/510, University of Michigan-Flint, Fall 2026
**Contact:** Reshu Jain, through the course (her email address and the team's Discord channel are left out of this public copy)
**If you get stuck, do not guess and move on — message us. A question from you usually means the guidelines are wrong, and fixing them helps everyone.**

---

## Read this first (2 minutes)

**You do not need any background in Lean, Six Sigma, or process improvement.** Everything
you need is on this page. If a term appears that is not defined here, that is a bug in these
guidelines — tell us.

**The short version of your job.** You will read a short story about something going wrong at
work — a delayed invoice, a mislabeled medication, a report nobody can find. For each story you
answer one main question and two sets of follow-ups:

1. **What kind of fix does this problem need?** Pick exactly one of five answers. This is the
   main question and it is a judgment call. (§3)
2. **What kinds of waste does the story describe?** Tick all that apply, from a list of eight.
   Zero is a valid answer. (§4)
3. **Seven quick questions about what the story does and does not tell you.** (§5)

**Roughly 2 to 3 minutes per story**, and 20 stories in a sitting. Some are two sentences, some
are two pages. The tool shows you a timer and records how long you actually took — that
measurement is part of the dataset, so please let it run honestly rather than rushing to look
fast. Taking longer than the estimate is not a problem; nobody is scored on speed.

**The single most important rule:** *label what the story says, not what you think is really going
on.* If the writer says they know the cause, you record that they know the cause, even if you
personally think they are wrong. You are describing the text in front of you, not diagnosing the
organization.

---

## 1. Why this task exists

When an employee reports a problem at work, someone has to decide what to *do* about it. Should
somebody just fix it this afternoon? Should a team spend a week on it? Should it become a
months-long data analysis project? Should the whole process be redesigned from scratch? Or is it
not really a process problem at all?

Getting this wrong is expensive in both directions. A five-minute fix routed into a four-month
statistical study wastes a year of somebody's life. A deep systemic problem "solved" in an
afternoon comes right back.

Today a trained practitioner makes this call by reading the request. We are building a dataset
so a model can learn to make the same call — which requires a set of narratives that humans have
read and routed. **You are that human.** Your labels are the answer key.

---

## 2. What one item looks like

Each item is one **process-problem narrative**: free text describing something going wrong in a
work process, written the way a person would actually report it. They come from public sources —
consumer complaints, federal audit reports, help-desk tickets, patient-safety case studies, and
question-and-answer sites. They are messy, uneven in length, and sometimes contain the writer's
own opinion about the cause. That is intentional. That messiness is the task.

The narratives arrive with **no labels of any kind**. Nothing in the source data tells you the
answer. That is why we need you.

**How two of the sources look.** The tool shows a one-line note above each of these:

- **Consumer complaints (CFPB).** The CFPB removes names, account numbers and exact dates before
  publishing. They appear as `[redacted]`, `[date]` or `[date in 2018]`. A redaction tells you
  nothing about the answer; read around it.
- **Help-desk tickets.** One item is a whole email thread between a customer and support, with no
  sender names and all in lower case as published. Names, systems and other details were replaced
  by the publisher and appear as `[user]`, `[system]`, `[SQL]` and similar. A new paragraph starts
  where a new message seems to begin. Label the problem the thread as a whole describes.

> **Example narrative**
>
> *"Vouchers sit in the approver's inbox for weeks, and about a third come back to us for rework
> because a line item was coded wrong. We have asked for the approval queue report but nobody can
> tell us why some approvers are so much slower than others. Finance says it is our data entry;
> we think it is their review step."*

---

## 3. Question 1 — Methodology (pick exactly one)

This is the main label. **Read the whole narrative before you pick.** Make the call the way a
reasonable person would after reading it once — then use the reference below to check yourself.

### The five answers

| Label | In plain English | Pick it when |
|---|---|---|
| **`JUST_DO_IT`** | *Somebody just go fix it.* | The story tells you both what is wrong **and** what would fix it, the fix touches one step or one team, and it sounds like hours or a couple of days of work. No study needed — just do it. |
| **`KAIZEN_EVENT`** | *Get the right people in a room for a few days.* | The problem is about **flow** — things waiting, being handed back and forth, duplicated effort, a clumsy layout, too many approvals. Roughly *why* it happens is understood; what is missing is a few days of focused work by the people who do the job. |
| **`DMAIC`** | *We need to measure before we can fix.* | An existing process is producing bad results — errors, delays, cost, wild variation — and **nobody knows why**. The story says the cause is unknown, or offers competing theories, or asks for analysis. Data exists or could be collected. |
| **`DMADV`** | *Design something that does not exist yet.* | There is **no process today**, or a brand-new capability is being requested, or the story says the current process **could never** meet the requirement even if it ran perfectly. This is a build/redesign, not a repair. |
| **`NOT_CPI`** | *This is not a process-improvement problem.* | The ask is really for money, headcount, a policy decision, a purchase, or compliance with a law — with no process problem inside it. ("CPI" = continuous process improvement.) |

### What the acronyms mean

You never have to use these words, but reviewers may ask, so here they are:

- **DMAIC** — Define, Measure, Analyze, Improve, Control. The standard five-step improvement
  cycle for an **existing** process whose failure cause is unknown. The "Measure" and "Analyze"
  steps are the whole point: you collect data to find the cause before changing anything.
- **DMADV** — Define, Measure, Analyze, **Design**, **Verify**. Same first three steps, but it
  ends in *designing something new* instead of improving something old. Used when there is
  nothing to improve, or when what exists is fundamentally incapable of the target.
- **Kaizen event** — Japanese *kaizen*, "change for better." A short, focused workshop (typically
  2–5 days) where the people who actually do the work redesign their own workflow. Fast and
  hands-on; not a statistical study.
- **Just Do It** — informal industry term for a fix obvious enough that any structured method
  would be overhead.
- **Not CPI** — our own catch-all for requests that arrive at an improvement team but are not
  improvement work.

### Repair or build: telling `DMAIC` from `DMADV`

These two are the easiest to mix up: the names differ by two letters and both start with
Define, Measure, Analyze. The difference is what they end with. **`DMAIC` repairs something
that exists. `DMADV` builds something that does not.**

Ask one question: **is there a process today that is supposed to produce this result?**

- **Yes, and it could work.** It works some of the time, for some people, at some sites, or it
  used to work. It is broken, not missing → a repair. If nobody knows why it fails, that is
  **`DMAIC`**. (If the cause is known, it is `KAIZEN_EVENT` or `JUST_DO_IT` instead.)
- **No.** Nobody owns it, it is done ad hoc by whoever gets the request, or the thing being asked
  for is brand new → **`DMADV`**.
- **Yes, but the story says it could never do what is now required**, even if everyone did every
  step perfectly: a new rule, customer need or target that the current design cannot reach →
  **`DMADV`**.

A process that **performs badly** is not the same as a process that **cannot perform**. Slow,
error-prone and inconsistent are all repairs. Only "does not exist" or "could never meet this,
even run perfectly" is a build.

| Sounds like `DMAIC` (repair) | Sounds like `DMADV` (build) |
|---|---|
| "about a quarter come back with errors" | "we have no process for…" / "there is no way to…" |
| "it varies by shift / approver / site" | "every department does it differently, on its own" |
| "it used to work" / "it got worse after…" | "the new rule requires…, and even when everything goes right we take…" |
| "we tried X and it did not help" | "we need to design this from scratch" |
| "we do not know why" | "the old system cannot do what is now asked" |

**When a fix has already been tried and did not work.** A failed fix tells you the cause was
guessed wrong, so the real cause is still unknown → **`DMAIC`**. Two exceptions: the story now
names a new, specific, small fix (for example, the first fix was right but one step was missed)
→ **`JUST_DO_IT`**; or the story says the process could never meet the requirement, however
well it runs → **`DMADV`**.

### How long each route takes, and who does it

This is background, to help you picture each route. **Do not choose a route because a job
sounds big or small**; choose it from what the story says about the cause, the fix and whether
a process exists. And in the seven questions (§5), answer "how big a job?" from the text only.

| Route | Typical length | Who does it | What you have at the end |
|---|---|---|---|
| `JUST_DO_IT` | hours to a couple of days | whoever owns that step | the fix, done |
| `KAIZEN_EVENT` | a 2–5 day workshop, with about 2 weeks of preparation and a few weeks of follow-up | the people who do the work, with a facilitator | a redesigned flow everyone has agreed to |
| `DMAIC` | about 4 months (commonly 3–6) | a trained lead and a small team, working with data | the proven cause, the fix, and a plan to keep it fixed |
| `DMADV` | about 5 months, often longer | a design team, with the people the process serves | a new process, designed and tested against the requirement |
| `NOT_CPI` | not an improvement project | managers or budget owners | a decision: fund it, staff it, approve it |

### One workplace, eight stories

The same office, with the facts changed. Read down the "clue" column: that is what decides the
route, not the topic.

| Story (a university facilities office) | Route | The clue |
|---|---|---|
| "The online work-order form still lists the old building names, so requests for the new science building go to the wrong crew. Add the new building to the list." | `JUST_DO_IT` | cause and fix both stated, one small change |
| "We moved the key cabinet to the loading dock, but crews still lose time because the cabinet code was never given to the night shift. Send them the code." | `JUST_DO_IT` | a first fix half-worked; the missing step is named |
| "A work order is emailed to the front desk, printed, walked to a supervisor, retyped into the scheduler and emailed to the crew. It waits a day or two at each hand-off. Everyone agrees the printing and retyping add nothing, and the office wants a few days to redesign the flow." | `KAIZEN_EVENT` | a flow problem whose cause everyone agrees on |
| "About a quarter of repairs have to be redone within a month. Some crews rarely have repeats and others often do, and it is worse in winter. We have three years of work-order records and no idea what drives it." | `DMAIC` | a process that exists, fails unevenly, cause unknown |
| "Last spring we added a sign-off checklist to cut repeat repairs. Repeats have not dropped, and we do not know why." | `DMAIC` | a fix was tried and failed, so the cause is still unknown |
| "The new residence halls open in the fall, and there is no way to request repairs there yet: no form, no assigned crew, and nobody who owns the requests." | `DMADV` | no process exists |
| "A new campus rule requires safety repairs within 24 hours. We schedule crews once a week, so even when every step goes right a request takes four days." | `DMADV` | the design can never meet the new requirement |
| "We need budget for three more electricians before the new buildings open." | `NOT_CPI` | only a budget and staffing request; no process problem described |

### If two answers feel close

Ask these in order and stop at the first one that clearly applies. **Use this only when your
first read was genuinely ambiguous** — it is a tie-breaker, not a formula. If you run it
mechanically on every item you will produce labels a simple script could have produced, and the
dataset becomes worthless.

1. Is the ask really for money, staff, policy, or a purchase, with no process problem inside it?
   → **`NOT_CPI`**
2. Is there no process today, or does the story say it could never meet a stated requirement
   even if run perfectly? → **`DMADV`**. A process that merely runs badly is a repair, not this.
3. Are the cause *and* the fix both stated, small in scope, and quick? → **`JUST_DO_IT`**
4. Is the rough cause understood, and is this a flow / hand-off / waste problem? → **`KAIZEN_EVENT`**
5. Otherwise → **`DMAIC`**

### Hard cases, decided in advance

| Situation | What to do |
|---|---|
| The writer states a cause, but also asks for a study. | **Trust the stated cause.** Then choose by scope and effort: `JUST_DO_IT` if small and quick, `KAIZEN_EVENT` if it needs a team. |
| The narrative contains two different problems. | Label the one the writer **leads with**. Describe the other in the note box. |
| "This process needs a complete overhaul." | That alone is **`DMAIC`**, not `DMADV`. Only choose `DMADV` if the story states a requirement the current process cannot meet, or says there is no process. |
| A fix was tried and did not work. | The cause was guessed wrong, so it is still unknown → **`DMAIC`**. If the story now names a new, specific, small fix → `JUST_DO_IT`. If it says the process could never meet the requirement → `DMADV`. |
| It works for some people, shifts or sites and fails for others. | A working process exists, so this is a repair: **`DMAIC`** if nobody knows why, `KAIZEN_EVENT` or `JUST_DO_IT` if the story says why. |
| A new system or tool is involved. | If the story is about designing how the work will run with it → `DMADV`. If it only asks to buy or fund it → `NOT_CPI`. If a current process is failing and the tool is someone's guess at a fix → label the failure (usually `DMAIC`). |
| A new law or regulation forces a change, and there is also a real process problem in the story. | Label the **process problem**. Mention the mandate in the note box. |
| Someone asks for more staff because the queue is backed up. | If the story describes *why* the queue backs up, label the **process problem** and note the staffing ask. If it is only "we need two more people," that is **`NOT_CPI`**. |
| The narrative is a complaint about an outcome with no process detail at all (e.g. "my claim was denied and nobody will explain why"). | Still label it. A denial with no explanation and no visible process is usually `DMAIC` (cause unknown, existing process). Set confidence to **low** and say why in the note. |
| You genuinely cannot tell. | Pick your best guess, set confidence to **low**, and write one sentence in the note box explaining what made it hard. Low-confidence items go to a third reviewer — they are useful, not failures. |

### One worked example per label

Each example shows the narrative, the answer, why that answer, and **why the other four are
wrong**. These are the calibration set — read all five before you start.

---

#### `JUST_DO_IT`

> *"The weekly status report template still points to the old SharePoint site, so every branch
> chief emails the analyst asking where the file went. We know the fix: update the link in the
> template and the pinned announcement. It is a thirty-minute job."*

**Why `JUST_DO_IT`:** cause stated (stale link), fix stated (update it), one step, thirty minutes.

**Why not the others:** not `DMAIC` — nothing to investigate, the cause is right there. Not
`KAIZEN_EVENT` — no team, no workshop, nothing to redesign; one person fixes it. Not `DMADV` —
the reporting process exists and works fine apart from one broken link. Not `NOT_CPI` — there is
a genuine process failure, it is just a small one.

**Wastes:** `MOTION` (people searching for the file), `WAITING` (chiefs blocked until the analyst
replies).

---

#### `KAIZEN_EVENT`

> *"Purchase requests bounce between procurement and the program office an average of four times
> before approval. Each side says the other is asking for information it should already have. We
> can see the handoffs in the ticket log; nobody has ever sat down and mapped the whole thing
> end to end."*

**Why `KAIZEN_EVENT`:** classic flow and hand-off problem. The cause is broadly understood
(duplicated information requests across a boundary), the data is already visible, and what is
missing is a few days with both teams in one room mapping the process.

**Why not the others:** not `DMAIC` — the cause is not a mystery requiring measurement; the
handoffs are visible in the log. Not `JUST_DO_IT` — it crosses two organizations and cannot be
fixed by one person in an afternoon. Not `DMADV` — a purchasing process exists; it is clumsy,
not absent. Not `NOT_CPI` — this is exactly process-improvement work.

**Wastes:** `TRANSPORTATION` (requests moving back and forth), `WAITING`,
`EXTRA_PROCESSING` (re-supplying information that already exists), `DEFECTS` (the bounce-backs
are rework).

---

#### `DMAIC`

> *"About 12% of lab results post to the wrong patient encounter. It is not one tech and not one
> analyzer — we have checked both. It happens more on night shift but not every night. We have
> two years of interface logs. We need to figure out what is actually driving it before we change
> the workflow."*

**Why `DMAIC`:** an existing process, a measurable defect rate, an explicitly **unknown** cause
(the obvious suspects have been ruled out), a real dataset available, and the writer says they
want to understand before acting. That is the textbook case for measure-then-analyze.

**Why not the others:** not `JUST_DO_IT` — there is no known fix. Not `KAIZEN_EVENT` — a
workshop would produce guesses; the pattern is intermittent and needs statistical work. Not
`DMADV` — the lab interface exists and works 88% of the time; it does not need redesigning from
zero. Not `NOT_CPI` — clearly process work.

**Wastes:** `DEFECTS` (wrong postings and the correction work they cause).

**What would change the answer:** if the writer said *"we traced it to one interface rule that
drops the encounter number; correct the rule,"* the cause and fix are known → `JUST_DO_IT`. If
they said *"we replaced the interface last year to fix this and the rate did not move,"* it is
**still `DMAIC`**: a failed fix leaves the cause unknown. It would only become `DMADV` if the lab
had no way to match results to encounters at all, or the story said no version of the current
set-up could meet a stated requirement.

---

#### `DMADV`

> *"We have no way to onboard contract clinicians. Credentialing, system access, and badge
> issuance are three separate manual email chains invented independently by three departments,
> and the new state rule requires a verified 10-day turnaround. Even if all three ran perfectly
> they would not hit 10 days."*

**Why `DMADV`:** there is no single process to improve — three ad-hoc chains exist instead — and
the narrative states explicitly that even perfect execution of the current arrangement cannot
meet the requirement. That is the "design something new" trigger.

**Why not the others:** not `DMAIC` — improving what exists is stated to be insufficient, so
measuring it would not help. Not `KAIZEN_EVENT` — you cannot streamline your way from "no
process" to a verified 10-day guarantee. Not `JUST_DO_IT` — no fix is stated and the scope is
enterprise-wide. Not `NOT_CPI` — the new rule is context, not the ask; the ask is to build a
capability.

**Wastes:** `WAITING`, `EXTRA_PROCESSING` (three parallel manual chains). Arguably none —
`DMADV` cases often have an empty waste list because there is no process yet to be wasteful.

**What would change the answer:** if one onboarding process existed and simply ran slowly for
reasons nobody understands, that is a repair → `DMAIC`. If everyone agreed the delay came from
three redundant sign-offs, → `KAIZEN_EVENT`. What makes this `DMADV` is what the text states
outright: no single process, and a requirement the current arrangement could never meet.

---

#### `NOT_CPI`

> *"Our team is down two analysts after the hiring freeze and we cannot keep up with the review
> volume. We need the positions restored in the FY27 budget."*

**Why `NOT_CPI`:** the entire ask is a budget and headcount decision. No process is described,
no failure mode is described, nothing about *how* the work happens. Nobody running an
improvement project could act on this.

**Why not the others:** not `DMAIC` — nothing to measure and no process described. Not
`KAIZEN_EVENT` — no flow described. Not `JUST_DO_IT` — restoring budget positions is not a
process fix. Not `DMADV` — nothing is being designed.

**Wastes:** none. **Careful:** if the same story had said *"we cannot keep up because every
review is manually re-keyed into two systems,"* that is a described process failure and it would
become a process label with `EXTRA_PROCESSING` — with the staffing ask recorded in the note box.

---

## 4. Question 2 — Wastes (tick all that apply, or none)

"Waste" is the Lean term for effort that costs something but does not help the customer. There
are eight standard categories. Tick every one the narrative **describes**. Do not tick one
because it is probably true in a workplace like that — only if it is in the text.

**An empty list is a perfectly good answer.** Many `DMADV` and almost all `NOT_CPI` items have
none.

| Waste | Plain English | Looks like |
|---|---|---|
| **`DEFECTS`** | Work done wrong and then redone | rework, errors, corrections, returned/rejected items, "sent back" |
| **`OVERPRODUCTION`** | Making more, sooner, or faster than the next step needs | reports nobody reads, batch processing ahead of demand, "just in case" copies |
| **`WAITING`** | People or work sitting idle | "sits in the queue for weeks," waiting on approval, blocked, downtime |
| **`NON_UTILIZED_TALENT`** | People's skills, ideas, or authority going unused | "nobody asked the nurses," staff not allowed to decide, suggestions ignored |
| **`TRANSPORTATION`** | Work items, materials, or information moving between places or systems | routed between offices, re-entered in a second system, mailed back and forth |
| **`INVENTORY`** | A pile of unfinished work, stock, or stored information | "a backlog of 200 cases," full queues, stockpiles |
| **`MOTION`** | People moving or searching unnecessarily | hunting for a file, walking to another floor, "nobody can find" |
| **`EXTRA_PROCESSING`** | Steps, approvals, or data entry beyond what is actually needed | triple approval, entering the same data twice, a form nobody uses |

*(Mnemonic: the first letters spell **DOWNTIME**.)*

### The five confusions that cause disagreement

| If you are torn between… | Use this rule |
|---|---|
| `WAITING` vs `INVENTORY` | Items **sitting idle** → `WAITING`. A **counted pile** ("backlog of 200") → `INVENTORY`. Both can apply. |
| `MOTION` vs `TRANSPORTATION` | **People** moving or searching → `MOTION`. **Work or information** moving → `TRANSPORTATION`. |
| `EXTRA_PROCESSING` vs `DEFECTS` | Doing **more steps than needed** → `EXTRA_PROCESSING`. Doing it **wrong and fixing it** → `DEFECTS`. **Rework is always `DEFECTS`.** |
| `OVERPRODUCTION` vs `INVENTORY` | Producing **ahead of need** → `OVERPRODUCTION`. The **pile it creates** → `INVENTORY`. Tick whichever the story emphasizes; both if both are explicit. |
| Is a staffing shortage `NON_UTILIZED_TALENT`? | **No.** That waste is about skills and ideas being ignored, not about not having enough people. |

### Worked example for wastes

> *"Claims print in the mailroom, get walked to the third floor for signature, walked back, then
> scanned into the imaging system by hand. Roughly one in five gets scanned upside down and has
> to be re-scanned. Adjusters keep a stack of about 300 waiting on signature at any time."*

**Ticked:** `TRANSPORTATION` (claims walked between floors), `MOTION` (the person doing the
walking), `EXTRA_PROCESSING` (printing and manual re-scanning of something already digital),
`DEFECTS` (upside-down scans requiring re-scan), `INVENTORY` (the stack of ~300),
`WAITING` (those 300 are idle).

**Not ticked:** `OVERPRODUCTION` — nothing is being produced ahead of need.
`NON_UTILIZED_TALENT` — nobody's skills or ideas are mentioned.

---

## 5. Question 3 — Seven questions about the narrative

These describe **what the text tells you**, not what you infer about the workplace.

> **Answer these *after* you have chosen a methodology.** The interface enforces this order on
> purpose — see §6.

| Question | Answers | What you are deciding |
|---|---|---|
| `process_exists` | yes / no / unsure | Is there any current process at all, even a bad one? |
| `cause_known` | yes / no / unsure | Does the writer claim to know **why** it happens? "We think it might be X" → **`unsure`**, not yes. |
| `solution_known` | yes / no / unsure | Does the writer state a **specific** fix? "Something needs to change" is not a fix. |
| `data_available` | yes / partial / no / unsure | Does the story mention measurable data that exists — logs, counts, reports, percentages? |
| `scope` | single_step / single_process / cross_functional / enterprise / unsure | How far does it reach? One task → `single_step`. One team's workflow → `single_process`. Two or more departments → `cross_functional`. Whole organization → `enterprise`. |
| `problem_type` | defects_variation / delay_flow / cost / safety / customer_requirement / new_capability / resourcing_policy / unsure | The **dominant** complaint. Pick one even if several apply. |
| `effort_estimate` | hours / days / weeks / months / unsure | **Only if the narrative implies it.** If the story gives you no sense of size, answer `unsure` — do not estimate it yourself. |

**`unsure` is a real answer and we want it.** A narrative that is silent about the cause is
genuinely different from one that says the cause is unknown, and the model needs to see that
difference. Do not fill in `yes`/`no` to look decisive.

---

## 6. Order of work, and why it matters

Work each item in this order. The interface will not let you skip ahead, and that is deliberate.

1. **Read the whole narrative.**
2. **Choose the methodology** on your overall read of the story.
3. **Tick the wastes.**
4. **Answer the seven questions.**
5. **Set confidence**, add a note if anything was non-obvious, submit.

**Why methodology comes first.** If you answered the seven questions first, you could derive the
methodology from them mechanically — "cause known plus solution known plus hours equals
`JUST_DO_IT`" — without ever exercising judgment about the text. Every annotator following that
shortcut would produce the same answers a ten-line script could produce, our five labels would
carry no information beyond the seven fields, and the dataset would not support a machine-learning
task at all.

The judgment we are capturing lives in the reading: deciding whether *"Finance says it is our
data entry; we think it is their review step"* counts as a known cause is exactly the call we
need a human to make. Choose the methodology from the story, then describe the story.

---

## 7. Confidence and notes

**Confidence** — how sure are you of the **methodology** label?

- **`high`** — you would defend this to a reviewer.
- **`medium`** — you think it is right, but a reasonable person could pick another.
- **`low`** — you are guessing. **Say so.** Low-confidence items are routed to a third reviewer
  and are among the most valuable items in the set, because they show where the guidelines are
  thin.

**Note box** — one sentence is plenty. Worth writing when: you were torn between two labels; the
narrative had a second problem in it; something in the text was contradictory or unclear; or you
think the guidelines do not cover this case. Never write anything here you would not want the
whole class to read.

---

## 8. Ground rules

- **Label independently.** Do not discuss items with other annotators while labeling. We measure
  how much you agree with each other; if you compare notes first, that measurement is
  meaningless.
- **Do not look anything up.** No searching for the source document, no asking an AI model what
  the label should be. We are recording *your* judgment from *this text*. (Using an AI to
  explain a term in these guidelines is fine and expected — using it to choose a label is not.)
- **You cannot break anything.** Your work saves in your browser as you go. Closing the tab or
  losing power does not lose your labels.
- **Take breaks.** Fatigue shows up in agreement scores. Ten careful items beat thirty rushed ones.
- **`unsure` and `low` confidence are honest answers, not failures.**

---

## 9. What happens to your labels

Your file goes into inter-annotator agreement analysis (Fleiss' kappa for methodology,
Krippendorff's alpha for wastes). Where several people labeled the same item, a majority vote
becomes the ground-truth answer key; a tie or a weak majority is settled by a vote weighted by
everyone's confidence and then checked by a team adjudicator. That key
trains and evaluates the models the class builds in later phases.

Your name appears only as an annotator ID in the dataset. Your individual labels are not graded
and disagreeing with the majority is not an error — it is signal about where the task is hard.

---

## 10. For our team: the annotation plan

*(The team's internal plan for the annotation round: time estimates, assignment design and the
pilot. It is left out of this public copy and kept in the private course repository.)*

---

## Changelog

| Date | Version | Change |
|---|---|---|
| 2026-09-10 | v0.1 | Initial draft. Practitioner-facing; assumed Lean Six Sigma background. |
| 2026-09-20 | **v1.0** | Rewritten for external annotators with no domain background. Added: plain-language overview and acronym glossary (§3); one fully worked example per methodology label with why-not-the-other-four reasoning (§3); a worked waste example (§4); seven additional pre-decided hard cases (§3); contact information; ground rules on independence and AI use (§8); per-item time estimate and the full assignment plan (§10). **Structural change:** methodology is now chosen *before* the seven intake questions, and the decision order is demoted from an algorithm to a tie-breaker (§6) — this prevents the methodology label from being a deterministic function of the intake fields, which would have made the task solvable by if-then logic and not a machine-learning problem. Interface enforces the order. |
| 2026-09-28 | v1.1 draft | §2: how CFPB complaints and help-desk tickets are shown. The batch builder now displays CFPB redactions as `[redacted]` / `[date]`, amounts without braces and normal spacing, and help-desk placeholders as `[user]`, `[system]` etc., with a paragraph per message; the tool shows a per-source reading note. Display only: the dataset keeps the source text. Prompted by batch items that reviewers found hard to read (e.g. CASE-000021, CASE-000236). |
| 2026-09-28 | v1.1 draft | Contact is now a UM email address and the team's Discord channel (both left out of this public copy); the GitHub-issue route is marked team-only, since classmates cannot open the private repository. Annotators return their file by email or Discord direct message, never in a public channel. Prompted by preparing the course's annotation-request form. |
| 2026-09-29 | v1.1 draft | §3: new "Repair or build" section separating `DMAIC` from `DMADV` with one question (is there a process today that is supposed to do this?) and a table of tell-tale phrases; a rule for a fix that was tried and failed (`DMAIC`, with two exceptions); a "how long each route takes" table, with a warning not to choose a route by job size; eight contrast stories from one workplace; tie-breaker step 2 reworded; three new hard cases (a failed fix, works for some but not others, a new system or tool). The tool's option help and reference panel carry the same text. Prompted by the practice round: `PRACTICE-03` and `-07` split 2 to 2 between `DMAIC` and `DMADV`, and 3 of the 4 `DMADV` answers also said a process exists. |
| 2026-09-30 | v1.1 draft | §9: agreement is Fleiss' kappa (9 raters per item, not 2), and ties are settled by a confidence-weighted vote checked by an adjudicator. §10: the round-1 roster is 9 annotators (5 external, 4 internal; the annotation lead does not label), so 9 labels per shared item, 45 coverage items and 60 labeled items; the practice round's measured time and results replace "the pilot has not run yet"; the gold-label rules from #27 are written out. No change to the labels or to what annotators are asked to do. |
| 2026-10-07 | v1.1 draft | §10: the course assigns us 12 external annotators, so the round-1 roster is 16 (`ext01` to `ext12`, plus the 4 internal annotators): 16 labels per shared item, 80 coverage items and 95 labeled items, with the gold-label bands restated as shares (13 or more of 16 high, 10 to 12 medium). Batches now go out as email or Discord attachments, with no shared folder. The tool's "What this means" and "Examples" panels open again (fixed by Reshu in #30, carried into the template), and the "Answer step 1 first" notices now disappear once step 1 is answered (they used to stay on screen). No change to the labels or to what annotators are asked to do. |
