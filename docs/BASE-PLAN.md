# DeadRamp Base: Plan (draft, Nov 14, 2026)

Status: brainstorm and plan, at Aries's direction. Build sequence: after fif-ears ships. Nothing here is built yet. This file is uncommitted working state in the deadramp repo.

## The idea in one line

DeadRamp stops being only text: the whole marketplace becomes a walkable VR base, generated from the repo's own data, where every vendor is a building and every service is a room you can stand inside.

## Ground truth it is generated from (measured Nov 14, 2026)

- `forks.json` registry: 781 offerings, 674 distinct vendors.
- 101 group directories on two axes: function (accounting, ai, cybersecurity, cloud-infrastructure-hosting, collaboration, crm, data-management, development-tools, and the rest) crossed with trust tier (L1, L2, L3, untiered).
- Impact levels: Moderate 450, High 124, Low 24, LI-SaaS 42, Unknown 141.
- Authorization status: FedRAMP Certified 547; pipeline states 234 (Initial Implementation 102, Legacy Ready 53, Agency In Process 46, FedRAMP In Process 33).
- Built state: 779 of 781 offerings built; 2 honestly unclassified (TERIDA CLASsoft, USDA vGov). 40 gap entries re-scoped to the platform layer under PLATFORM-LAYER.md; union merges carry parent lineage.

The Base is a VIEW over this data, never a second source of truth. When the catalog changes, the Base regenerates.

## Layout law: one spiral, at every scale

Design reference (Aries, Nov 14, 2026): the worlds of Skyrim, Oblivion, and Dragon Age 2, where travel distance is governed by winding paths at every size, so a compact world feels vast. His words: things are a distance of a spiral no matter how close or far, small or large, it is all spirals. The spiral is therefore scale-invariant in the Base, not just the street plan:

- World scale: a single spiral boulevard is the whole map. Districts (the function groups) are placed in order along the spiral; inside a district, vendor buildings line the boulevard in registry order.
- District scale: each district is its own smaller spiral off the main boulevard, so entering a district feels like descending into its own coil.
- Building scale: inside a tower, floors are reached by a spiral ramp or stair around a central atrium, one offering per turn; a small office is a single coil.
- Room scale: inside a large service room, exhibits and terminals arrange around a spiral path from the door to the service's core exhibit.
- Why it matters mechanically: path length is always much longer than straight-line distance, which is what makes those game worlds feel big, and here it doubles as the streaming budget: you are always turning, so the engine only ever owes you the next arc of the coil, at every scale.
- Wayfinding is the law Aries named: everything is one spiral away. You can always reach anything by following the spiral inward or outward; you cannot get lost in a grid.
- The spiral is also the performance trick: sightlines curve, so draw distance stays short and districts stream in and out naturally on weak hardware.
- Placement is deterministic math (parametric spiral, fixed spacing rules), not hand placement: same catalog in, same city out, seed-locked and testable.

## Buildings and rooms

- One building per vendor (674). Height and footprint scale with offering count: a single-offering vendor is a small office; a multi-offering vendor is a tower, one floor band per offering.
- One room per offering (781). The room is the service: its name, tier badge, status, and its real build data on the walls: the service's own controls, its reference implementation's API surface on a working terminal panel, its source listing one tap away.
- Rooms are archetypes per function, data-filled per service (hand-building 781 unique rooms is not the path; archetype plus real data is): cybersecurity gets an ops-center archetype (log streams, control-family panels), cloud hosting a server hall, AI a lab, collaboration a meeting space, accounting a ledger office, and so on across the function axis. The animation in a room matches what the service does.
- Status is architecture, honestly: Certified offerings are finished, lit buildings. Pipeline offerings are under construction: scaffolding, cranes, exposed frame, in proportion to their status. The 2 unclassified offerings are surveyed empty lots with a plaque saying exactly that. Platform-layer entries get a shared platform deck, not fake buildings. The Base never overstates the data.
- Union merges are skybridges. As built, the bridges render the merge record DeadRamp actually carries: the UNION-SPEC build lineage, 19 parent edges across 18 builds, because the records contain no vendor-to-vendor merges. Each bridge joins the gates of the two districts where the child and parent builds' offerings live, and the merge rule (union of baselines, highest tier inherited) is the exhibit on the bridge's record card.

## Stack (quality over ego, per Aries)

- Rendering: Three.js in the browser, WebXR for VR. One build serves Quest Browser (Quest 2 and newer), phones (touch twin-stick, optional gyro look), and desktop (WASD plus mouse). No app store, no sideload, standards-first like everything else in the portfolio.
- World generation: the Polyglot Procedural Engine supplies the procedural city and building math (it already generates cities with zero asset files). Where PPE has no piece and an open-source library does it better, the library wins: Aries's order is quality, not ego. All generation is procedural from the catalog; zero hand-modeled assets required for v1.
- Data pipeline: a small exporter in this repo emits `base-catalog.json` from `forks.json` plus the group structure (district assignment, spiral coordinates, room archetype, status styling), consumed by the generator.

## Performance budget (Quest 2 is the floor)

- Exteriors: instanced shells, merged geometry per district, one texture atlas.
- Interiors: only the building you are inside is fully built; every other building is a shell. Rooms in a building build on entry, release on exit.
- Targets to verify on device, not assume: stable frame rate in VR on Quest 2 in the densest district, draw calls and memory inside budget, load from URL to standing in the plaza in seconds, not minutes.

## Movement and orientation

- Walk: WASD and mouse on desktop, twin virtual sticks on phone, smooth plus teleport locomotion with comfort options in WebXR.
- Directory kiosks at spawn and at each district gate: search a vendor or service, and either get a lit path along the spiral or teleport. The spiral remains the ground truth under every shortcut.

## Build phases

- Phase 0: catalog exporter and schema; fidelity tests (building count equals vendor count, room count equals offering count, every room's data matches the registry).
- Phase 1: spiral city exterior: districts, buildings, labels, lighting; walkable on desktop and phone; performance budget measured.
- Phase 2: interiors v1: lobby plus service rooms for the top function archetypes, in-room panels from real build data.
- Phase 3: WebXR pass: Quest Browser VR, controller locomotion, comfort settings; verified on Aries's own Quest 2.
- Phase 4: full archetype coverage across all function groups; merge skybridges; platform deck; construction states for pipeline vendors. As built (Nov 15, 2026): the skybridges render the UNION-SPEC build lineage (19 edges), the records holding no vendor-to-vendor merges; the platform deck presents the 40 re-scoped entries carried in GAPS.md (the gaps batch decision document accounts for 39 closures: 36 platform re-scopes and 3 written re-scopes; the deck follows the fuller record, and the accounting note is kept in LAYOUT.md); construction states scaffold the 227 buildings with pending offerings in proportion to each vendor's uncertified share.
- Phase 5 (later, optional): guided tours, and multiplayer walkthroughs over WebRTC using the Collaborative MIDI pattern (manual connect codes, no servers).

## Verification doctrine (same as the rest of the portfolio)

- Determinism test: same catalog, byte-identical layout data.
- Fidelity tests: counts and per-room data against `forks.json`; a mutated catalog entry must change exactly its own building and room (negative control).
- Sensory test: actually walk it, on phone and in the headset, before any claim ships.

## Open questions for Aries when the build starts

- Naming inside the world: district names from the function axis as-is, or base-style designations (e.g. call-signs) mapped to them?
- First district to finish end-to-end as the reference standard: cybersecurity is the natural flagship (largest tiered set), but his call.

## Brand layer and integrity standard (Aries, Nov 14, 2026)

The one-line constitution, in Aries's words: it is our version of each FedRAMP vendor, their products, their services, their office, built by us from the public record.

The Base is built to government contractor standards: it represents the vendors with integrity and is never rushed or sloppy. Two layers govern every building:

- The federal grammar (the constant): one institutional architecture language across the whole Base, order, symmetry, serious materials, security detailing, gravitas. This is what makes 674 vendors read as one federal installation.
- The brand layer (the variable): inside that grammar, each building wears its vendor's own brand identity, starting with color scheme (Aries's example: Meta is blue and white), then finishes and interior character as phases deepen. The building should be recognizable as that vendor before you read the sign.

Framing, stated in the world (spawn kiosk and building cards): each space is a model of the vendor built from public information, to our understanding of them. No endorsement is claimed or implied; the mirroring is representation, not affiliation. Integrity rules: a vendor's brand colors are used only when they are established public identity (catalog field palette_source: researched); otherwise the building takes the neutral federal finish (palette_source: default) rather than invented colors. The full 674-vendor brand research is its own unhurried pass, not a Phase 1 sweep.

Legal line for the brand layer (Aries, Nov 14, 2026): no trademark or copyright violation, with clear source origin. Vendor names are used nominatively from the FedRAMP Marketplace data to identify what is modeled. Color schemes are evocation only (a palette, never their artwork): no logos, logotypes, wordmarks, brand fonts, mascots, or trade dress elements are reproduced, anywhere, ever. The framing text (a clean-room model built from public FedRAMP Marketplace information, inspired by each vendor's public brand identity, not affiliated with or endorsed by any vendor) lives in exactly one place inside the experience: the Settings panel, under "About this model" (placement rule amended by Aries, Nov 15, 2026: a disclaimer is not an immersive feature, so it is not repeated per building or per room, not on walls, panels, cards, or signs). The README keeps the text as repository documentation. "Inspired by" is the register: origin is unmistakable, affiliation is never implied.

Rendition principle (Aries, Nov 14, 2026, his analogy: how South Park puts celebrities in the show): recognizability is carried by a few identity cues rendered in the Base's own style, never by reproducing the subject's own works. For a celebrity that is name plus likeness shorthand in the show's crude animation; for a vendor here it is name plus public color palette plus the character of their FedRAMP services, rendered in the Base's federal architecture. The depiction is unmistakably ours, the identity is unmistakably theirs, and endorsement is never implied. Our ground is simpler than parody: factual documentation of a public government marketplace, nominative naming, no logos or trade dress, and the standing not-affiliated framing.

Generic-medicine principle (Aries, Nov 14, 2026): the Base's version of each vendor is like generic medicine, not the main brand. Same active ingredient: the service itself, its function, controls, and data, modeled faithfully from the public record (DeadRamp's clean-room builds are the ingredient). Different label and packaging: our federal rendition, our name for the shelf, and a label that states plainly it is not the brand product and claims no affiliation. Generics are legitimate because they prove equivalence and label honestly; the Base's equivalent is its fidelity tests (every room's data matches forks.json exactly) plus the standing inspired-by framing.

Care without fog (Aries, Nov 14, 2026): the build is careful so it cannot bite later, but caution never costs clarity. The caution governs the rendition only (our style, honest labels, no brand artwork, no implied affiliation). The facts are never blurred, because the facts are public spending: the FedRAMP Marketplace is the public's own record of what the government buys, so vendor, product, tier, status, and controls are stated plainly. Public spends are public.

Experience bars (Aries, Nov 14, 2026): the Base must be immersive, innovative, and genuinely fun to experience, a place, not a data viewer with walls. It is a digital twin of the whole FedRAMP spend: the core information design is legibility, anyone walking it can see who is getting what and who is doing what (vendor, services, tier, authorization status readable at a glance, from architecture before signage). Two honesty rails: (1) no misrepresentation of what DeadRamp already built, the twin mirrors the repo's real state, including the 2 unclassified lots, platform-layer deck, and reference implementations labeled as reference implementations; (2) it is stated clearly and repeatedly that we re-did it all, clean-room, so nothing in the Base is or implies an official endorsement by any vendor or agency. Data rail: the twin shows only what the public record carries (offerings, tiers, statuses, service models, source links); no invented dollar figures or facts.

## Video deliverables: one per phase, plus the completion film (Aries, Nov 14, 2026)

When the Base is complete (all phases, fully working), Muse produces a polished walkthrough video of Muse testing the finished Base, with voiceover and whatever else is needed to explain it, made nice enough for Aries to post to YouTube. Sent to Aries in chat; he posts it manually. Shape: real captured footage of the working Base (spawn and plaza, the spiral boulevard, a branded district street, a building record card, interiors, and the Quest view where feasible), narration covering what DeadRamp is, the twin philosophy (our version of each vendor, clean-room, inspired by, no endorsement), the fidelity numbers, and how to walk it. No claims the footage does not show.

Per-phase amendment (Aries, Nov 14, 2026, minutes later): videos are required for EACH phase, not only at completion: a playthrough of Muse playing through each phase's working build, with voiceover and/or captions added as needed to explain what is being done on screen. The completion film remains the final, polished YouTube piece; the per-phase videos are the running record. Phase 1's video is produced retroactively from the shipped v0.1.0 build.

Master documentary (Aries, Nov 14, 2026): the per-phase videos are progress checks, sent to Aries in chat as each phase verifies. When all phases and all phase videos are done, they are combined into one master video: a full documentary of building DeadRamp Base, with the completion walkthrough as its finale. The phase videos are therefore shot and narrated as chapters of that documentary from the start (consistent title cards, narration voice, caption style), so the master is an assembly, not a re-edit from scratch.

Platform-prompt rule (Aries, Nov 14, 2026): there is no "press E" on VR or cellphone. Every interaction prompt and affordance must match the platform in the visitor's hand: keyboard language on desktop, tap language and tappable targets on touch, controller/gaze language in WebXR. Help text adapts to the detected input class; no instruction may name a control the current device does not have.
Tutorial lifecycle rule (Aries, Nov 14, 2026): guidance behaves like an in-game tutorial, present when it teaches, gone when it has taught. Help text shows on arrival and at first entry into a new space, then fades; it never floats above the simulation indefinitely. A small persistent help affordance recalls it on demand.
