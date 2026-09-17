# Third-party notices

APT's original scaffold is AGPL-3.0-only; see [LICENSE](LICENSE). The licence text is the unmodified
GNU Affero General Public License version 3, copyright Free Software Foundation, Inc.

Runtime dependencies are installed from the exact hashes in `uv.lock`; their wheel distributions
retain upstream licence/copyright notices in their `.dist-info` directories in the runtime image.
FastAPI and Pydantic use MIT; Uvicorn uses BSD-3-Clause. Transitive distributions and their notices
must remain included. Python uses the PSF licence and Debian image components retain their own
notices under `/usr/share/doc`; this file does not relicense them.
The exact installed runtime licence identities are recorded in
[the runtime inventory](docs/runtime-licenses.json); licence texts remain in the installed wheels.

uv is an MIT/Apache-2.0 build tool, not a scientific runtime. Development tools are separately
locked. Scientific extraction installs pysweph 2.10.3.6 (AGPL-3.0), Swiss 2.10.03,
Shapely 2.1.2 (BSD-3-Clause), its GEOS 3.13.1 (LGPL-2.1-or-later), and NumPy 2.5.3
(BSD-3-Clause plus its individually licensed bundled native libraries). All exact original
notices, native-source lineage and replacement/relinking requirements remain in the reviewed
inventory below. No Swiss Professional entitlement is claimed.

TBB 2026c comprehensive/no-oceans geometry and the embedded catalog are ODbL-1.0 data,
not relicensed under APT's program grant: Timezone Boundary Builder; OpenStreetMap contributors
(https://www.openstreetmap.org/copyright). See https://opendatacommons.org/licenses/odbl/1-0/.
The unchanged dataset is acquired separately with its exact public source/license evidence.
IANA tzdata/tzcode 2026c notices and build sources are retained alongside the exact compiled
TZif artifact recipe. Swiss DE441 data files retain their upstream licence/source notices.

The pre-extraction [native/source compliance inventory](compliance/README.md) now retains exact
scientific sources/data, native-source lineage and the original public base-image notices.
It does not by itself establish scientific parity. Preserve all original notices
and source/replacement rights described there before any later binary distribution.

The inventory's `publication_evidence` is only an upstream PyPI HTTPS publication record and
subject-hash consistency check. It is **not** independently verified Sigstore/Fulcio/Rekor
attestation and is not proof of a bit-reproducible upstream compiler build. Preserve this scope
statement whenever that evidence is summarized in release notes or source-offer metadata.
