# Bundle verification review fix — local Linux evidence

The visible PR review reported that changing an ignored candidate's manifest
digest did not fail the original 84-test suite. Those tests checked generation
in isolated fixtures; they did not audit that selected saved candidate.

The fix adds the read-only `verify` CLI and the shared
`verify_candidate_bundle` / `load_verified_model` functions. Invalid manifests,
changed bytes, missing files and inconsistent metadata are rejected before
deserialization. The model loader uses a verified in-memory copy. Members 2–3
must call the reader in their evaluator and translate invalid required evidence
into a blocked gate outcome; their consumer integration remains pending.

Local checks: Ruff lint and formatting passed; the complete suite passed
**122 tests with one existing dependency warning**. The raw results are in
`review-integrity-lint.txt`, `review-integrity-format.txt` and
`review-integrity-pytest.txt`.

A synthetic negative control deliberately removed the digest comparison. The
model-corruption regression then failed with exit 1 before any model was loaded.
The verifier source was restored byte-for-byte and the same regression passed
with exit 0. See `review-integrity-negative-control.txt` and
`review-integrity-restored-control.txt`. This was a controlled local test, not
a GitHub CI run, gate decision or manipulation of the real course candidate.

The earlier unprefixed records describe the initial Member 1 preparation;
`review-integrity-*` records describe this subsequent fix. No real candidate
was evaluated or deployed here. Windows verification, actual GitHub CI on the
new PR revision and independent review are still required. Only the visible
review request has been assessed; the other comment and missing context must
also be checked.
