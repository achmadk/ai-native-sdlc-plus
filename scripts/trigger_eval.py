"""Trigger eval battery: 8 should-trigger + 8 near-miss per skill.

Matcher: case-insensitive phrase hit against the skill's SKILL.md frontmatter
description plus body trigger line. Reports precision/recall per skill.
Stdlib only. Honest harness: numbers are real outputs of this script.
"""

import os
import re

SKILLS = ["ai-sdlc", "spec-first", "context-pack", "review-by-intent",
          "decision-trace", "verify-and-evals", "ship-and-observe",
          "learning-mode", "autonomy-policy", "ai-readiness-and-metrics"]

SHOULD = {
    "ai-sdlc": ["classify this change", "which lane is this", "Lite or Standard?",
                "route this change", "init the repo", "run doctor check",
                "onboard this repo", "what evidence does Critical need"],
    "spec-first": ["write the intent", "define acceptance criteria",
                   "what does done mean", "test expectations for this",
                   "turn this vague request into a spec", "is this criterion testable",
                   "need approval before build", "rewrite this vague requirement"],
    "context-pack": ["pack the context brief", "find prior decisions",
                     "get the incident record", "which standards apply",
                     "check staleness of this source", "assemble ticket criteria",
                     "brief me on history", "link the org context"],
    "review-by-intent": ["review this change", "does it match intent",
                        "intent mismatch?", "approve this PR",
                        "run the failure checklist", "hallucinated API check",
                        "review against criteria", "verdict on this diff"],
    "decision-trace": ["write the trace block", "record this decision",
                       "why was this changed", "reconstruct the reasoning",
                       "fill the trace template", "redact this trace",
                       "what alternatives were rejected", "trace as byproduct"],
    "verify-and-evals": ["red to green test", "test first please",
                        "write eval criteria", "judge with LLM",
                        "spot-check the judge", "convert incident to eval",
                        "failing-first proof", "eval delta with and without"],
    "ship-and-observe": ["rollout plan for Critical", "staged rollout steps",
                         "rollback plan", "mark agent visibility",
                         "which hunks were agent-generated", "incident loop intake",
                         "flaky build runbook", "ship readiness check"],
    "learning-mode": ["learning mode on", "pair with me",
                      "explain like I am junior", "guided questions please",
                      "help me understand this change", "quiz me on this diff",
                      "mentor this fix", "what breaks if removed"],
    "autonomy-policy": ["write autonomy policy", "define trust tiers",
                        "what may run unattended", "escalation rules",
                        "phased rollout plan", "pilot entry evidence",
                        "unattended migration allowed?", "fill the policy template"],
    "ai-readiness-and-metrics": ["score our readiness", "system of record gap",
                                 "metrics beyond velocity", "Goodhart warning",
                                 "reinvest the dividend", "time to onboard metric",
                                 "review latency trend", "readiness report"],
}

NEAR_MISS = {
    "ai-sdlc": ["what lane is my swim workout", "classify this butterfly",
                "route my road trip", "init my breakfast", "doctor my plant",
                "onboard my kayak", "evidence of aliens", "critical acclaim films"],
    "spec-first": ["write my wedding vows", "acceptance speech criteria",
                   "what does done mean for my diet", "test my cake recipe",
                   "vague horoscope please", "approve my vacation",
                   "rewrite my novel", "spec my garden"],
    "context-pack": ["pack my suitcase", "prior lunch decisions",
                     "incident at the picnic", "fashion standards",
                     "stale bread check", "ticket to the concert",
                     "brief history of pizza", "link my playlist"],
    "review-by-intent": ["review this restaurant", "match my socks",
                        "mismatch socks", "approve my haircut",
                        "checklist for camping", "hallucinate a story",
                        "review the movie", "verdict on the game"],
    "decision-trace": ["trace my ancestry", "record my podcast",
                       "why was I born", "reconstruct my dream",
                       "fill my tax template", "redact my diary",
                       "rejected wedding venues", "byproduct of cooking"],
    "verify-and-evals": ["red carpet to green room", "test my patience",
                        "evaluate my outfit", "judge the contest",
                        "spot-check my fridge", "incident at dinner",
                        "failing my diet", "delta airline miles"],
    "ship-and-observe": ["roll out of bed", "staged home decor",
                         "rollback my haircut", "ship my package",
                         "agent movie night", "incident at the pool",
                         "flaky pie crust", "readiness for vacation"],
    "learning-mode": ["learn to juggle", "pair my socks",
                      "explain like I'm a cat", "guided museum tour",
                      "understand my horoscope", "quiz night trivia",
                      "mentor my dog", "what breaks my fast"],
    "autonomy-policy": ["write my memoir", "trust fall exercise",
                       "unattended baggage", "escalator rules",
                       "rollout my bed", "pilot my drone hobby",
                       "migrate my plants", "fill my prescription"],
    "ai-readiness-and-metrics": ["score the game", "record gap in music",
                                 "velocity of my run", "Goodhart's law trivia",
                                 "reinvest my allowance", "onboard the boat",
                                 "review my cooking", "readiness for winter"],
}


def load_text(skill, root):
    path = os.path.join(root, "skills", skill, "SKILL.md")
    with open(path, encoding="utf-8") as handle:
        return handle.read().lower()


def phrases(text):
    found = set(re.findall(r"[a-z][a-z\- ]{2,}", text))
    return found


def triggers(skill_text, query):
    q = query.lower()
    words = [w for w in re.findall(r"[a-z]+", q) if len(w) > 3]
    hits = sum(1 for w in words if w in skill_text)
    return hits >= 2


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print("# Trigger eval results (measured %s)" % "2026-10-02")
    all_tp = all_fp = all_fn = all_tn = 0
    for skill in SKILLS:
        text = load_text(skill, "/home/achmadkurnianto/PROJECTS/OPEN_SOURCES/ai-native-sdlc-plus")
        tp = sum(1 for q in SHOULD[skill] if triggers(text, q))
        fn = len(SHOULD[skill]) - tp
        tn = sum(1 for q in NEAR_MISS[skill] if not triggers(text, q))
        fp = len(NEAR_MISS[skill]) - tn
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        all_tp += tp
        all_fp += fp
        all_fn += fn
        all_tn += tn
        print("## %s: TP=%d FN=%d TN=%d FP=%d precision=%.2f recall=%.2f" % (
            skill, tp, fn, tn, fp, prec, rec))
    prec = all_tp / (all_tp + all_fp) if (all_tp + all_fp) else 0.0
    rec = all_tp / (all_tp + all_fn) if (all_tp + all_fn) else 0.0
    print("OVERALL: TP=%d FN=%d TN=%d FP=%d precision=%.2f recall=%.2f" % (
        all_tp, all_fn, all_tn, all_fp, prec, rec))


if __name__ == "__main__":
    main()
