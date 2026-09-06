# show-me Skill — Patent / Paper Commander Research Sync

Date: 2026-09-06
Status: RESEARCH_INPUT / PENDING_VERIFICATION
Source type: External AI Agent Skill / implementation reference
Source identified by user: HumanLayer `show-me` Skill (GitHub: humanlayer/skills, plugin `show-me`)
Sync targets: AI Agent Patent Commander + AI Agent International Journal/Paper Commander
Disclosure priority: PATENT-FIRST

## User-provided reference summary

`show-me` is presented as a Claude Code-oriented Skill that lets an AI Agent choose a suitable visual representation instead of returning only long prose. Reported output modes include:

- Pseudocode — logic/process explanation
- Call Tree — execution/call sequence
- Mermaid — sequence diagrams / flowcharts
- File Tree — project structure
- Diff — change comparison
- HTML — complex visual explanation / infographic-style output

The claimed operating idea is not to use every visualization every time. The Agent selects a representation according to the information/problem being explained.

The example supplied by the user uses RAG: question → retrieve/search knowledge → obtain relevant evidence → provide question + evidence to LLM → grounded answer. The visual explanation is intended to reduce the cognitive burden of a long prose-only answer.

## Blacklight Factory relevance

Candidate for Reuse-First discovery/adaptation. Do not rebuild the basic visualization Skill from scratch without discovery evidence.

Potential DAYONG adaptation concept (`DAYONG-show-me`):

- Pseudocode: algorithms / decision logic
- Call Tree: Agent → API → Worker execution chains
- Mermaid: Workflow / State Machine / Agent topology / governance gates
- File Tree: repository and project structure
- Diff: before/after engineering changes
- HTML: chairman/executive visual reports

Suggested trigger policy: invoke visualization selectively for complex process, architecture, comparison, code-change, meeting-decision, and research-framework explanations; avoid unnecessary visualization for simple answers.

## Patent Commander note

Treat the external `show-me` Skill as prior/external implementation reference, NOT as DAYONG novelty evidence. Potentially relevant research question: whether DAYONG has a distinct patentable mechanism in which an Agent/system classifies task/information structure and selects an output/explanation modality under governance, role, evidence, audience, or workflow-state constraints. This must be compared against prior art before any novelty claim.

Patent-first disclosure rule applies: do not publicly disclose potentially novel DAYONG extensions before patent review/filing decision.

## Paper Commander note

Potential research relevance: Agent explainability, human–AI collaboration, cognitive load, multimodal/visual explanation selection, operational transparency, and visualization of Agent/workflow execution evidence. It may serve as an implementation/reference case after source verification; it is not by itself formal academic literature.

Possible empirical variables for later consideration: comprehension time, task accuracy, perceived explainability, cognitive load, decision confidence, error-detection rate, and comparison of prose-only vs adaptively selected visual explanation.

## Governance / Reuse-First disposition

Decision status: APPROVED_DISCOVERY / ADAPTATION_CANDIDATE, pending source/license/dependency/security verification.

Required path before implementation:
External source verification → license/dependency/security review → Sandbox PoC → DAYONG adaptation decision → tests → runtime evidence → registry.

Do not treat screenshots/social-post claims as verified technical facts until source/runtime verification is completed.
