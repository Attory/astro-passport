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
locked. No Swiss Ephemeris, Python Swiss binding, timezone-boundary or tzdb data is distributed
by this scaffold. No Swiss Professional entitlement is claimed. Before adopting any of them,
retain the exact distribution, upstream copyright/licence files, checksums, data provenance and
redistribution requirements in a new reviewed inventory. A dependency name alone is not clearance.
