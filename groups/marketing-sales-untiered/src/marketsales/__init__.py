"""Marketing & Sales — untiered set (Operation DeadRamp, Phase 2
remainder, Untiered Set 18).

A records substrate for the two untiered Marketing & Sales forks:
opportunity, evaluation, capture-pipeline, proposal-content, and
workflow-registry records on the business-development side;
contact-list, audience-segment, campaign, delivery, suppression,
and engagement records on the outbound-email side. **Tier null**:
every member's FedRAMP impact level is Unknown in the source, so
no tier is assigned, no CMMC equivalence is drawn, and no control
baseline is asserted — the build answers to the forks' documented
control claims only. Python standard library only.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
