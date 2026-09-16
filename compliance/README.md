# Native/runtime Corresponding Source controls

Scope: the exact Linux/amd64 CPython 3.12.14 scaffold and the **proposed**, not installed,
scientific dependencies. These are independently authored compliance tools, public upstream
identities and original public-image notices, not ACE implementation/history/corpora. APT is
AGPL-3.0-only; original third-party licences remain controlling for their components.

## Evidence and operation

- `source-lock.json`: 396 exact artifacts, SHA256, size and credential-free HTTPS location.
  Discovery status is deliberately not an approval flag. Reviews/approval belong in the ledger.
- `base-image.json`: all 105 Debian binary/source identities and all 105 original copyright
  files, CPython licence, pip identity and immutable public-image build history; not host data.
- `correspondence.json`: 73 Debian source-version groups verified against `.dsc` SHA256 lists;
  103 Cargo source archives/notices; native section matches; 27 matching Swiss C/header files;
  original wheel-notice hashes.
- `discovery-inputs.json`: maintainer acquisition inputs. `expand.py` derives Cargo source pins
  from retained pydantic-core Cargo.lock. Discovery never updates a release implicitly.

From the exact public APT checkout using Python 3.12 (new output files required):

```sh
python -m compliance.bundle fetch --lock compliance/source-lock.json --cache /absolute/source-cache
python -m compliance.bundle verify --lock compliance/source-lock.json --cache /absolute/source-cache
python -m compliance.audit --lock compliance/source-lock.json --cache /absolute/source-cache --output /absolute/correspondence.json
python -m compliance.bundle pack --lock compliance/source-lock.json --cache /absolute/source-cache --output /absolute/sources.tar
python -m compliance.validate
```

The cache/bundle is outside Git. No AAC/ACE access or account is required. Archives are never
executed or extracted to the filesystem by these tools. Packaging is byte-deterministic with
sorted hash members and fixed metadata; upstream compiler bit-reproducibility is **not** claimed.
Missing/corrupt bytes fail closed. Debian SHA1s are locators only; final integrity uses SHA256,
including `.dsc` correspondence. Debian signature verification is not claimed.

Complete source archives, patches, source RPM, Cargo crates, build controls and notices are
retained, not merely licence summaries. Exact reference wheels/data are retained for lineage.
An operator remains responsible for availability: mirror/retain the bundle alongside any binary
distribution, rather than relying forever on upstream URLs. GitHub Actions artifacts requiring
login are not the public source offer. All acquisition URLs were exercised successfully.

## Exact image and release controls

`python -m compliance.build --output /absolute/image-source.json` requires a clean checkout,
verifies anonymous public availability of the exact commit, and builds from `git archive HEAD`
(not ignored/untracked files). It records image ID, source SHA, source-lock hash and archive URL.
It does not push an image, publish a release or deploy. Only Linux/amd64 is covered.

The Dockerfile pins base/build-tool digests and frozen hashed dependencies. It does not upgrade
OS packages. uv is a general-purpose build tool absent from the final image; base pip 25.0.1
is separately inventoried. Runtime notices must not be stripped. Fast CI checks coverage/drift;
the full offline audit verifies retained bytes. The scaffold still installs no science.

Before **any image distribution/activation**, retain and verify:

1. the exact public APT source archive with build/install controls and later extracted code;
2. the source bundle/hash at an anonymous HTTPS location offered alongside the binary;
3. image digest ↔ source SHA ↔ source-lock/bundle hash and successful availability checks;
4. original notices and the replacement/rebuild instructions below;
5. exact deployed `/source` and `/health/version` correspondence.

A private URL, licence label or source for a different image is insufficient. No scientific
image exists yet: its later extracted code and generated TZif controls must be public at that
image's exact revision before distribution. This task does not copy them or waive that release
gate. Changed binaries/platform/build controls require new evidence and independent review.

## Rights/obligations matrix

| Component | Exact source/lineage | Licence and fulfilment |
|---|---|---|
| APT | Exact public commit and build controls | AGPL-3.0-only; complete Corresponding Source/network access, notices; no Professional entitlement. |
| pysweph 2.10.3.6 / Swiss 2.10.03 | Binding `9dd0ca73345406addd5597ccb30488391b61cd1a`, Swiss `5ae0bce00dbc66c6315c86da20518e3dd138255b`, complete archives/sdist/wheel | Binding AGPL-3.0-or-later (select v3); Swiss AGPL route. Preserve binding/Astrodienst notices. All 27 core C/header files match exactly; not a claim of rebuilding the wheel bit-for-bit. |
| Swiss DE441 sepl/semo | Data at upstream `91339e55d2351f32548d8a8d5bca6aa93b4f6da7`, exact files and complete Swiss source | AGPL route; Swiss copyright/data notices and JPL/DE441 attribution. |
| Shapely 2.1.2 / GEOS 3.13.1 | Exact wheel/sdist, build controls `5fb639d1056888d135fe56bfaf750c9648addeec` explicitly build GEOS 3.13.1, complete GEOS source | BSD-3-Clause / LGPL-2.1 respectively; full notices, sources and replacement rights. Shapely BSD alone is insufficient. |
| NumPy 2.5.3 | Exact wheel/sdist, release controls `a1cc2f4a9705f4171d480263fde93fa01ba816d6` | BSD plus bundled MIT/0BSD/Zlib/CC0/native notices retained; no blanket BSD claim. |
| OpenBLAS/LAPACK | scipy-openblas64 0.3.34.106.0 wheel, source `446c436e10450c348169808f1a6b3fae0925c9f7`, build controls/patches `78fc0eaf6de71d92fd98f74f7e5bfa356a2f83e3` | BSD-3-Clause/LAPACK notices. NumPy library's listed executable/read-only sections/build ID match upstream wheel; auditwheel dynamic-metadata changes mean whole files differ. |
| gfortran / quadmath | AlmaLinux `8.5.0-28.el8_10.alma.1` binaries → exact SOURCERPM header → GCC source RPM, patches/spec | GPL-3.0-or-later WITH GCC Runtime Library Exception 3.1 / LGPL-2.1-or-later respectively. Exact code/read-only sections/build IDs/debuglinks match. Retain full sources/notices even where eligible-compilation exception limits obligations; never apply that exception to quadmath. |
| Pydantic core 2.46.5 | Exact wheel/sdist plus all 103 Cargo.lock registry sources, including target/dev supersets | MIT and original crate terms; choose MIT where offered, preserve Apache/Unicode/Zlib/LLVM exception terms where applicable. r-efi notices live in AUTHORS; wit-bindgen missing crate notices retained from exact VCS `f2393e6e98fa5f9236cac580db8a3fc9de6a4b70`. |
| Statically linked Rust runtime | Native core ELF compiler string/path identifies Rust 1.98.0 commit `88d9e12ae178fab0fb5cc050a94da85685d449ea`; complete matching Rust source distribution retained | MIT/Apache and original bundled runtime/LLVM notices. Original native notices are included in the image, not only referenced by SPDX labels. |
| CPython 3.12.14 | Exact tar.xz digest in base history, Docker-library recipe source archive | PSF and full embedded/historical notices. Recipe/history preserve configure/build flags. |
| pip 25.0.1 and Python runtime packages | Exact archives/wheels/uv.lock; base pip separately covered | MIT/BSD and all vendored notices; full runtime dependency closure, not only direct packages. |
| 105 Debian binaries / 73 source versions | Original copyright files, Snapshot source archives, `.dsc`, patches/build rules | Every original licence controls (GPL/LGPL/permissive/etc.); full matching sources retained, not omitted under a blanket System Libraries exception. |
| TBB 2026c comprehensive/no-oceans | Exact geometry archive/catalog plus upstream source/DATA_LICENSE | ODbL-1.0 database / MIT builder. Retain © OpenStreetMap contributors and TBB attribution; offer exact database and any later derivative database as required, separate from AGPL code. |
| IANA tzdata/tzcode 2026c | Exact source archives and source-specific notices | Public-domain/BSD terms; never substitute OS tzdata 2026b. Generated TZif is not distributed before its approved public build controls accompany it. |

Original licences control over this summary. Rights to private ACE history, fixtures,
compatibility/scoring, participant/sex methodology, social services or AIS are not granted here.

`native-notices.json` preserves verbatim original texts (deduplicated by original SHA256 with
every origin listed). JSON encoding preserves even original whitespace and is checked by hash.
The Docker image retains it in addition to wheel/base notices. PyPI
publication evidence for NumPy/pysweph is retained and its subject hashes checked; this does not
claim independent Sigstore signature verification or prove every upstream compiler build step.

## Modification/replacement/relinking

There is no restriction on modification or reverse engineering for debugging library changes,
no signing key needed to run a modified image, and no device installation lock. Recipients can
rebuild from public sources. For GEOS: use the retained CMake build/install, then rebuild Shapely
with `GEOS_INCLUDE_PATH`/`GEOS_LIBRARY_PATH` pointing to that prefix. For quadmath/gfortran: use
the retained GCC source RPM spec/patches; rebuild OpenBLAS using its retained wrapper controls,
patches and ILP64 flags, then rebuild NumPy with that library. Full application source is
available for relinking. Rebuild dependants rather than blindly replacing hashed SONAMEs.

Scientific hash checks distinguish the approved reference from modifications; recipients may
legally modify those checks, relink and run their own newly identified service. Modified results
must not masquerade as approved parity. General-purpose compilers can be obtained normally;
shipped runtime/library sources are retained regardless of narrower runtime/system exceptions.

Maintain source availability for the exact distributed version; repeat the full audit before
release. Public-only reviewers receive only this repository's material, never private corpora.
The 103 Cargo entries (including target/dev supersets, not a claim all are linked) and 27 Swiss
C/header files are deliberate version-specific coverage checks. A dependency change requires
reviewed source-lock/`expand.py` regeneration and an explicit corresponding count update in
`validate.py`; never bump a count merely to silence an unexplained failure.
