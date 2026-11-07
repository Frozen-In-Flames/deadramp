# Platform layer — the written decision

Applies to: every group build in this repo, at every tier, and to the
36 GAPS.md entries triaged `rescope-platform` in the final batch.
Ratified with the batch disposition decision, 2026-11-07
(gaps-batch/DECISION.md).

Some requirements recur in group after group because they are
properties of the platform a build is deployed on, or of the
organization embedding it — not functions of the records substrate
each group implements. Registering them as per-group gaps forever
would misstate them: they are decided once, here, and each group's
entry closes by reference to this decision.

## The decisions

1. **Identity and authentication (IA-2, IA-2(1)/(2), IA-5).**
   Multifactor authentication, authenticator management, identity
   proofing, and any identity-provider, SSO, directory, PAM, or IGA
   engine stay with the embedding organization and its identity
   provider. Builds ship RBAC and access hooks and demo identities
   that are explicitly hooks, not an IdP. No build in this repo is, or
   claims to be, an identity provider.

2. **FIPS-validated cryptography (SC-13).**
   No build claims FIPS-validated cryptography. The builds are Python
   standard library only; the standard library is not a FIPS-validated
   module. Where a fork's own platform carries a validation (for
   example a FIPS 140-2 Level 3 HSM), that posture is the fork's, is
   recorded as the fork's, and does not transfer to the build.

3. **Encryption at rest and in transit (SC-28, SC-8).**
   Encryption at rest is a deployment-layer property of the storage
   the embedding organization provisions. Encryption in transit is
   TLS when configured at deployment. Builds perform no cryptography
   of their own except where a group's spec explicitly implements a
   mechanism (for example hash-chained audit), and never claim a
   validated module for it.

4. **Audit retention enforcement (AU-11).**
   Builds produce append-only audit records and never delete them.
   Retention-period enforcement — how long records are kept, and
   their eventual disposition — is the embedding organization's
   records schedule, executed at the deployment layer.

5. **Session lock and termination (AC-11, AC-12).**
   Builds authenticate per request and are stateless between
   requests; there is no build-side session to lock or terminate.
   Session policy belongs to the embedding organization's access
   layer in front of the build.

6. **Hosting substrate and platform umbrella.**
   A fork's hosting substrate (a named cloud, region, or impact-level
   posture of its own platform) does not transfer to the build.
   Multi-tenancy, hosting, and console surfaces are deployment
   properties unless a group's own spec claims a records function for
   them, in which case that function is a build gap in its own name —
   never closed by this umbrella decision.

## What this decision does not do

It does not close any function a group's spec actually claims. It
does not raise any build's tier or baseline: FedRAMP authorizes
products and CMMC certifies organizations, and the tier language in
this repo remains a planning equivalence, never a credential claim.
And it does not delete any gap entry: each entry closed under this
decision keeps its full text in GAPS.md with its status changed to
`re-scoped`.
