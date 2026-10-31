"""DeadRamp Phase 2, remainder untiered set — Talent Management,
tier null (the founding L2 substrate carried whole, re-anchored).

A clean-room records substrate for the candidate-facing talent
acquisition surface the group's two forks describe: organization
and candidate registries, requisition records, talent pipeline
definitions with candidate placements whose current stage is
derived from append-only stage-movement records (every movement
bounded by the pipeline's stage list), recruitment event and
registration records, assessment records (caller-supplied outcome
labels, never computed scores), video and in-person interview
records, and a workflow definition registry that records and
never executes — over an append-only audit log. Records and
opaque caller-supplied references only: no candidate's real name,
contact detail, resume, assessment content, or interview
recording is ever stored, and nothing about any candidate is ever
scored, ranked, or matched.
"""

__version__ = "0.1.0"
