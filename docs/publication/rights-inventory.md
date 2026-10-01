# Exact public-source rights inventory — 2026-10-01 candidate

Authority: Anton's “PUBLISH AND ACTIVATE APT END TO END” instruction grants public
APT AGPL-3.0-only publication and permits Apache-2.0 for the implementation-neutral
schemas/codec **only if** the provenance inventory permits it. This record
documents the inspected scope, not a blanket legal opinion or a licence change
to ACE, Unbubble, scientific data or unrelated AAC material.

| Surface | Origin and authorship evidence | Published terms |
| --- | --- | --- |
| `passport_codec/{__init__,codec,conformance}.py`, `PINS.json`, `fixtures/golden-v1.json` | New original science-free transport/conformance work first committed in APT `75380df`; task history identifies project author Attory. It implements public CBOR/COSE/Ed25519 interfaces and AAC0010's approved wire facts. No ACE calculation, private methodology or copied scientific source. Four file hashes frozen in `PINS.json`; golden values are synthetic. | Apache-2.0, version 1.0.0, local `LICENSE` and `NOTICE` |
| `contracts/accepted/schema.json` and byte-identical `contracts/astropassport/v1/schema.json` | Neutral schema independently authored in AAC proposal `30869d5`, accepted at `75092aa`, exported to public APT at `99056e6`. Same project-author history; accepted bytes SHA-256 `6d02118dd7b5ed16f52e1a67d2b270da53d070afe83c58e934484a0db5e8467c` remain unchanged. AAC ADR0002 defines the single canonical tagged URL. | Apache-2.0 only for these exact files, scoped by `contracts/NOTICE`; canonical tag protection and resolved SHA remain release gates |
| APT application, scientific extraction, build/tests | Original public scaffold plus the 13 narrow adapted destinations from 16 ACE origins listed with exact hashes and human project-rights attestation in AAC pre-extraction `acceptance.md`/`rights-inventory.json`. Three other origins were not copied. No private Git history, member data or compatibility method is imported. | AGPL-3.0-only; root `LICENSE`, origin records and upstream notices preserved |
| Other contract documents, scientific artifacts and third-party distributions | Original notices and precise provenance in `THIRD_PARTY_NOTICES.md`, `docs/runtime-licenses.json`, `compliance/{source-lock,correspondence,native-notices}.json`. TBB/OSM is ODbL; IANA and Swiss sources retain their original terms. | Original respective terms; **not** covered by the narrow Apache grants |

The codec's external dependencies are pinned cwt 3.3.0, cbor2 5.9.0 and
cryptography 50.0.2, with their own runtime distributions/notices retained in
the image and complete matching source in the compliance bundle. No dependency
source is vendored into `passport_codec`. A clean isolated wheel install and
four offline synthetic signature vectors must pass before publication. The
source/wheel package must include its own `LICENSE`, `NOTICE`, pins and fixture.

The 2026-10-01 public-tree audit used `gitleaks git --log-opts=--all` across
APT history: zero findings. Tracked paths matching private-key/credential/
member filename patterns: zero. These scans are not a guarantee against every
undetectable disclosure; the exact release diff/tree and public archive still
require inspection before push. No key, credential, real birth record, private
ACE methodology or private Unbubble source is in this scoped inventory.

Publication and deployment are distinct gates. This document records the
candidate prior to final commit/tag, hosted source-offer check and activation.
