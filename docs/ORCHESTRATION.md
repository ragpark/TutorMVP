# Orchestration

Next-best-action types: `START_NEW_LO`, `REVIEW_LO`, `PRACTICE_LO`, `REMEDIATE_PREREQUISITE`, `TAKE_DIAGNOSTIC`, `ASK_TUTOR`, and `COMPLETE_ASSESSMENT`.

Rules are deterministic and explainable. No assessment history recommends diagnostic. Weak prerequisite mastery below `.70` recommends remediation. LO mastery below `.60` recommends practice/review. Stale mastered objectives can be reviewed after two weeks. Every recommendation includes a human-readable reason and alternatives.
