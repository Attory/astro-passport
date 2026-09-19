# CP-014 Western facts MVP candidate

Human-authorized additive profile: `western-synastry-core.v1-mvp`.
This is an explicit MVP candidate, not a replacement for the accepted AAC v1
contract or either existing profile. No compatibility methodology enters APT.

`AstroPassportWesternResponse.v1-mvp` contains an unchanged
`sun-moon-lahiri.v1-mvp` response in `base` and `WesternCoreFacts.v1-mvp`.
The old tropical and Lahiri request/response schemas and content encodings are
unchanged. New requests opt in using their profile field; unknown versions fail
closed. Authentication, durable quotas, bounded workers and deadlines are shared.

## Scientific policy

Bodies are ordered Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus,
Neptune, Pluto, true North Node. Native identifiers are explicit. All longitudes
are tropical geocentric apparent ecliptic-of-date with requested/returned Swiss
flags exactly 2. Any fallback flag, warning or malformed result is rejected.
The existing exact Swiss/binding/data/Delta-T/tidal policies remain pinned.
South Node is not calculated here; consumers may derive it by exact +180 degrees.

Placidus uses `swe.houses_ex(UT1, latitude, longitude, b"P", 0)` under
`swiss-placidus-ut1-tropical-cusps.v1-mvp`. Coordinate order and UT1 are explicit.
Swiss's dummy zero cusp is omitted; the twelve cusps are in numbered order.
ASC equals cusp 1 and MC cusp 10. Flags 0 mean tropical, with nutation.
The binding raises on undefined Placidus geometry, including polar locations;
this becomes `status: unavailable`, `reason: placidus_undefined`, with no
fabricated axes or cusps. The native Porphyry fallback is never consumed.
Planetary facts remain available. Other failures remain bounded service errors.

Each longitude has the existing exact binary64 hex and half-even nine-decimal
representation, normalized to [0,360). Strict validation checks both forms,
body order, flags, coherent Sun/Moon and a single positive circular cusp cycle.
Serialization preserves arrays. Canonical content uses only E9 integers for
angles, under `apt.western-synastry-core-content.v1-mvp`; it includes the base
provenance/content and explicit new scientific policies. Source revisions remain
provenance, not endpoint names. No compatibility weights or meanings are included.

House-overlay consumers must name their policy: zodiac-longitude cusp intervals
are not Swiss's three-dimensional `swe_house_pos` calculation. This profile
provides cusp facts and does not make that methodological choice for clients.

Reference: [Swiss programming manual](https://www.astro.com/swisseph/swephprg.htm),
`swe_houses_ex`, `swe_houses`, `swe_calc`, and `swe_house_pos` sections.

## Evidence and deployment boundary

Public tests use independently synthetic dates/geography, never private birth
fixtures. They compare all eleven bodies/axes/cusps to the pinned native API,
repeat canonical outputs, preserve old profile bytes, exercise 1900/2100,
explicit polar unavailability, API authentication and invalid shape rejection.
The native reference explicitly uses DE441 tidal acceleration, matching the
worker; automatic global native defaults are not an acceptable reference.

New source bundle and exact-head CI are required before deployment. Existing
consumers pin source revisions, so rollout must coordinate consumer configuration
without weakening verification. APT deployment has not occurred at this checkpoint.
