Sprint 6 – Guided Knowledge Acquisition
Sprint Goal

The Digital Career Twin can actively improve itself by conducting a context-aware interview that identifies opportunities to deepen evidence, clarify uncertainty and capture user preferences.

Unlike CV ingestion, which extracts existing information, Guided Knowledge Acquisition elicits information that is absent, implicit or personally meaningful.

The interview should demonstrate that the Twin remembers previous evidence, reasons about the user's career, and asks thoughtful questions that materially improve the fidelity of the Twin.

**Objectives**

Introduce conversational acquisition as a first-class capability.

The Twin should:

identify opportunities to improve itself;
ask context-aware questions;
capture new evidence;
capture preferences and aspirations;
update the Twin accordingly.

**Architectural Position**
Twin
    ↓
Knowledge Acquisition Agent
    ↓
Interaction
    ↓
Knowledge Interpretation
    ↓
Twin Mapper / Reconciliation
    ↓
Twin Repository
    ↓
Mirror

where "Knowledge Interpretation" is the equivalent of the Extractor in document ingestion.

Unlike document ingestion:

Source
    ↓
Extractor

the interview begins with the Twin itself.

**Interview Philosophy**

The interview is not a questionnaire.

It is a guided investigation driven by the Twin's current understanding.

Every question should have a reason.

The Twin should never ask questions merely because they appear on a script.

Instead, questions should arise from:

uncertainty;
missing evidence;
unusual transitions;
incomplete roles;
emerging patterns;
user objectives;
opportunities to strengthen or challenge existing inferences.

**Interview Sessions**

The interview should support incremental knowledge acquisition.

A complete Twin should emerge through many short conversations rather than a single exhaustive interview.

The Knowledge Acquisition Agent should retain awareness of previous interview topics and preferentially explore areas where the expected information gain is highest.

**Interview State**

Current topic

Question history

Open hypotheses

Evidence added

Outstanding follow-ups

Completion status

**Three Areas of Exploration**
1. Past

Purpose

Improve the evidence layer.

Examples

achievements omitted from the CV;
lessons learned;
significant projects;
leadership examples;
career transitions;
gaps;
motivations behind decisions.

Primary output

New Evidence.

2. Present

Purpose

Understand current professional identity.

Examples

current responsibilities;
work preferences;
strengths;
frustrations;
current priorities.

Primary output

Reflection refinements.

3. Future

Purpose

Populate Preferences.

Examples

desired role;
industries;
aspirations;
capabilities to develop;
preferred work style;
trade-offs.

Primary output

Preferences.

**Question Generation Principles**

Every question should satisfy at least one of the following:

Completion

The Twin knows something is missing.

Example

"This project mentions a major transformation but no measurable outcome."

Clarification

The Twin has multiple plausible interpretations.

Example

"Datavant appears to be your first Platform Engineering role. Had you been performing similar work earlier under different terminology?"

Expansion

The Twin believes a role is underrepresented.

Example

"You marked this as one of the defining roles in your career. Would you like to explore it in more detail?"

Reflection

The Twin seeks to understand meaning rather than facts.

Example

"Looking back, which role most influenced the way you lead technology organisations today?"

Preference

The Twin seeks desired future state.

Example

"What type of technology organisation would you most like to lead next?"

**Question Quality Contract**

Every generated question should:

demonstrate awareness of the existing Twin;
explain, implicitly or explicitly, why it is being asked;
avoid asking for information already known;
maximise expected information gain;
minimise cognitive effort.

The interview engine should preferentially generate questions from professionally significant observations, including career transitions, emerging patterns, underrepresented roles, and areas of uncertainty.

Poor

Tell me about Datavant.

Better

Your Twin suggests that Datavant marked a shift toward enterprise AI and Platform Engineering after years of technology transformation work. What attracted you to the role, and did it meet your expectations?

**Conversation Principles**

Conversation should be used only when natural language adds value.

Conversation is appropriate for:

stories;
explanations;
motivations;
achievements;
reflections;
aspirations.

Conversation should not be used where a simple control captures the information more effectively.

**Interaction Model**

The Mirror should combine:

Conversation

for knowledge acquisition.

Controls

for calibration.

Examples of calibration:

role importance;
foundational role;
future relevance;
agreement with a reflection.

These controls are outside the scope of this sprint but should influence future interview prioritisation.

**Twin Updates**

Interview responses may create or modify:

Evidence

New achievements.

Projects.

Metrics.

Leadership examples.

Lessons learned.

Career context.

Reflection

Clarify existing observations.

Strengthen or weaken interpretations.

Preferences

Career objectives.

Desired future.

Role preferences.

Industry preferences.

Working style.

Values.

**Mirror Updates**

The Mirror should reflect interview outcomes by:

incorporating new evidence into the appropriate role;
updating affected inferences;
refreshing the Overview Brief;
updating Preferences where appropriate.

Preference editing and interactive negotiation are outside the scope of this sprint.

**Opening Gambit**
Purpose

The first question establishes the Twin's credibility.

Before requesting additional information, the Twin should demonstrate that it has already formed a thoughtful understanding of the user's professional history.

The user should feel that the Twin has studied their career rather than merely parsed their CV.

Design Principles

The opening question should:

demonstrate memory;
demonstrate reasoning;
identify a genuinely interesting observation;
invite elaboration rather than confirmation;
create curiosity through insight, not surprise.

It should never feel like onboarding.

Sources of Opening Questions

The Twin should preferentially select observations with high professional significance, including:

major career transitions;
unusually rapid progression;
repeated recurring themes;
apparent contradictions;
foundational roles;
emerging professional identity;
unexplained shifts;
strong but incomplete inferences.
Poor Opening

Tell me about your current role.

or

What would you like to achieve?

These are generic questions that could be asked without any understanding of the Twin.

Better Opening

Across four uploaded CVs, your Twin sees a consistent pattern of replacing bespoke ways of working with scalable engineering capabilities. That theme appears in banking, retail and life sciences, despite those industries having very different problems. Was that a conscious direction in your career, or is it something that only became obvious when looking back?

Notice what's happened.

The Twin isn't asking for facts.

It's offering an observation and inviting reflection.

Or:

Your Twin identifies your move into enterprise AI as one of the most significant transitions in your recent career. Looking back, do you see that as a genuine change in direction, or the continuation of a much longer interest that simply wasn't visible in earlier roles?

Again, the question demonstrates that the Twin has already been thinking.

Or:

Your career contains repeated examples of measurable operational improvement—reducing costs, increasing delivery speed, improving reliability—but your CVs say relatively little about what motivated that way of working. Where do you think that focus on measurement came from?

Now the Twin is exploring identity rather than chronology.

For every potential question, the Knowledge Acquisition Agent could estimate:

Insight — Does this reveal that the Twin has understood something non-obvious?
Personality — Is this question specific to this individual?
Information gain — Will the answer materially improve the Twin?
Engagement — Is this a question the user is likely to enjoy answering?

The highest-scoring question becomes the opening gambit.

Stretch goal: The first question should be impossible to ask without first building the Twin.
A generic AI can ask:

"Tell me about your career."

Only a Digital Career Twin can ask:

"I've noticed this distinctive pattern across fifteen years of your career that isn't explicitly stated anywhere you've shared. Help me understand whether it's real."

**Domain Boundary**

The Knowledge Acquisition Agent exists solely to improve the Digital Career Twin.

Every interaction should contribute directly to one or more of:

Evidence
Reflection
Preferences
Inferences

If a request cannot reasonably improve the Twin, the agent should politely decline to perform it within the interview and, where appropriate, suggest returning to the Twin.

Every conversational turn should have an expected contribution to the Twin.

In Scope

Examples include:

Adding or refining professional evidence.
Exploring career transitions.
Understanding motivations and aspirations.
Clarifying uncertainty.
Expanding underrepresented roles.
Improving the quality of the Reflection.
Capturing professional objectives and preferences.

Out of Scope

The interview should not become a general-purpose conversational assistant.

Examples include:

Writing software.
General knowledge questions unrelated to the Twin.
Creative writing unrelated to the user's professional life.
General productivity assistance.
Mathematical or technical tutoring unrelated to the Twin.

**Out of Scope**
External interviews.
Continuous interview scheduling.
Visualisations.
Preference editing controls.
Role calibration controls.
Multi-session interview planning.

**Acceptance Criteria**
✓ The user can initiate an interview from an existing Digital Career Twin.

✓ The first interview question references one or more facts, inferences or uncertainties already present in the Twin.

(Verifiable by inspecting the question and the underlying Twin.)

✓ Every interview question includes a machine-readable rationale identifying one or more of:

evidence_gap
clarification
expansion
reflection
preference

(May be hidden from the production UI but available in developer mode.)

✓ The interview engine generates questions dynamically from the current Twin rather than selecting from a fixed question sequence.

(Verifiable by running interviews against materially different Twins.)

✓ Every interview response is classified as one or more of:

Evidence
Reflection
Preference

✓ Evidence generated during the interview is processed through the existing Reconciliation Agent before being committed to the Twin.

✓ Interview responses classified as Evidence update the appropriate role or create new evidence where appropriate.

✓ Interview responses classified as Preferences create or update Preference objects within the Twin.

✓ If interview responses modify the Twin, the Mirror is regenerated before the next user interaction.

✓ The interview engine does not ask for information already explicitly represented in the Twin unless the purpose of the question is clarification.

Notice that "unless the purpose..." is important. You don't want to prohibit questions like:

"Your Twin identifies Datavant as your first explicit Platform Engineering role. Had you been doing similar work earlier?"

The Twin knows about Datavant. It doesn't know whether the interpretation is correct.

✓ The interview can generate questions from each of the following categories:

Completion
Clarification
Expansion
Reflection
Preference
Knowledge Gain

✓ Every interview response that introduces new information results in either:

a new Evidence item;
an updated Evidence item;
an updated Reflection;
a new or updated Preference.

Otherwise you've technically had an interview that accomplished nothing.

Traceability

✓ Every interview-generated addition to the Twin records interview provenance.

For example:

Source
Interview

Prompt ID

Timestamp

Conversation turn

That keeps interviews first-class evidence sources, consistent with the architecture.
