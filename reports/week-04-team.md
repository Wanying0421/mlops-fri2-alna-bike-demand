# Week 4 team report

## Lab 7 — Training pipeline, evaluation and quality gate

### Member 1 / Lead: implementation prepared for review

Source snapshot: `7d7e10fd3a3f36533c077732d21d07177fad32d6` (`m3`).
The source archive was inspected; no claim is made here that the current cloud
service has been independently verified.

Member 1 added a separate input-check/training entry point. It validates the
frozen data and splits, fits on 2011 only, and writes a uniquely identified
candidate with byte hashes, configuration, dependency lock, environment,
training revision and partition identities. It never writes the accepted model,
accepted pointer, existing tracking database or legacy metrics report.

Training exit 0 means `trained`, with `evaluation_status: not_evaluated`.
It does not mean eligible, accepted or deployed. Training requires committed
inputs. Failed/interrupted candidates have no completion marker, and rerunning
an existing ID is refused. Synthetic tests cover the preservation of accepted
files, train-only fitting, identity hashes, collisions, incomplete execution,
mid-run input changes and invalid model settings.

The legacy main-push deployment job generated the CI smoke fixture before cloud
deployment and only echoed a verification message. It was removed to prevent
automatic fixture promotion during Lab 7 integration. The two CI verification
jobs remain. This change does not alter the existing live service.

The team interface and ownership proposal is in
[`docs/lab7-contract.md`](../docs/lab7-contract.md). The initial design choices
are in the README's **Pipeline and gate** section. Local check scope and raw
results are in [`evidence/lab7/member1/`](../evidence/lab7/member1/).

### Results still required before completion

- Independent review, author response, green checks on the actual PR revision
  and manual merge of Member 1's component.
- Reviewed and committed policy with justified thresholds, operational limits
  and candidate/compute budget **before** real candidate evaluation.
- Actual trusted accepted reference, three-way validation evaluation and
  complete quality/operation/integrity decision evidence.
- One end-to-end command producing a decided candidate after the evaluator and
  gate are integrated; the current commands cover input checks and training.
- Independent rejection challenge showing unchanged accepted and served state.
- Durable immutable version storage, exact-byte manual promotion from reviewed
  green main, verified live identities and retained previous bundle/revision.
- Final evaluation, decision and state design answers, evidence links and
  recovery handoff for Lab 8.

No real candidate validation score, gate result, promotion or live service
verification is reported by this Member 1 preparation. Each member must also
submit their own private `reports/week-4.md`; this team report does not replace it.
