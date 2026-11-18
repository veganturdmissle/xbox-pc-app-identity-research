# Xbox PC app catalog and cloud-streaming identity research

## Public research summary

This project investigated how the Xbox PC app decides which products and cloud-streaming titles a Windows client may see, open, purchase, or launch. The central question was whether a small client-side identity change could make the app behave like an Xbox console, particularly for products or cloud titles normally excluded from PC.

The evidence says no: there is no single `Xbox Series X`, `Windows.Desktop`, or operating-system string that controls the entire experience. The app and Microsoft services apply several independent gates. A client-side change can affect one gate without changing the others.

The project did prove several narrower and useful points:

- The Xbox PC app can be made to display and open a console-only store product when a missing search result is supplied locally in the exact response shape the app expects.
- Selecting the console cloud offering changes the cloud title catalog returned to the PC client.
- Neither result grants console eligibility. Store actions remain filtered by PC services, and cloud session creation independently checks authenticated device identity.
- Cosmetic device values in request bodies and headers are not sufficient to pass that authorization check.
- The decisive cloud classification is carried through signed authentication material and cannot be changed by editing an ordinary request field.

No installed Xbox package file was modified during the experiments. Tests used reversible, narrowly scoped request observation or substitution, and temporary proxy/certificate changes were removed after each live test.

## Scope and safety of this report

This is a public-safe synthesis of the project record. It intentionally excludes:

- names, email addresses, gamertags, account identifiers, subscription details, and other personal data;
- passwords, login material, cookies, authorization headers, tokens, API credentials, private keys, and certificate files;
- device serials, hardware make/model values, exact OS fingerprints, network identifiers, and user-specific filesystem paths;
- raw captures and opaque session or correlation identifiers;
- step-by-step instructions for installing a traffic-interception certificate or redirecting account traffic.

Public product identifiers, application versions, generic service behavior, error names, and credential-free code findings are retained where they are necessary to make the results reproducible and technically meaningful.

## Research questions

The work addressed five related questions:

1. Which code path creates an Xbox PC cloud-streaming session?
2. Which client values describe the device as a PC, and where do they originate?
3. Does choosing the console cloud offering reveal a different title catalog?
4. Can ordinary device metadata make the service authorize a console-only title on PC?
5. Why can a console-only store product be absent from PC search even though the PC app can render its public product page?

## Method

The findings combine static analysis and controlled runtime experiments against Xbox PC app package version `2612.1001.23.0`.

Static work included:

- inventorying the packaged executables, libraries, manifest, Hermes bundle, and embedded web-client archive;
- tracing the native cloud session request builder and device-information serializer;
- tracing the Gaming Services device-authentication and XSTS request builders;
- locating catalog, search, hydration, product-detail, and cloud-offering routes in shipped client code;
- comparing static predictions with values observed during a successful cloud session.

Runtime work included:

- recording a successful, unmodified PC cloud-streaming session as a baseline;
- changing one variable at a time in offering, title, OS, and device-metadata experiments;
- comparing PC and console cloud title lists;
- observing the PC app's store search and downstream catalog hydration traffic;
- injecting a schema-compatible search entry to test whether the app could navigate to a console-only product;
- testing whether a device-family query substitution changed product details or actions;
- analyzing token structure without publishing or retaining decoded personal claims in report output.

The local interception helpers were designed around exact host, path, product, and baseline-value checks. Unexpected shapes are preserved rather than rewritten. The current automated suite contains 39 focused tests covering host filtering, exact-target rewrites, idempotence, malformed input, correlated search injection, and credential-safe summaries.

## A four-gate model

The strongest result is that the app's behavior is best understood as four separate gates:

| Gate | What it controls | What the project showed |
|---|---|---|
| Store discovery | Whether a product appears in PC search | The PC search service can omit a console-only product before downstream catalog hydration occurs. |
| Product details and actions | Whether the PC service returns layouts, purchase/install actions, and entitlements | Opening a product page does not make PC-only service routes return console actions. |
| Cloud title catalog | Which titles the cloud service lists for an offering | Selecting the console offering changes the returned catalog, even from the Windows app. |
| Cloud session authorization | Whether a listed title may actually start on the authenticated device | A separate server check rejects a console-only title when the authenticated client remains classified as Windows. |

This separation explains several results that would otherwise look contradictory. A product can be visible but not purchasable in the app. A cloud title can be listed and even show entitlement metadata but still be rejected at session creation. A device header can look like a console while the signed authentication chain still identifies the client as Windows.

## Application architecture and active streaming path

The examined package contains 57 PE files: 8 executables and 49 libraries. All are native 64-bit Windows binaries rather than managed .NET assemblies. The most relevant components are the primary Xbox app hosts, the web/native bridge, the React Native and Hermes runtimes, Gaming Services integration, WebRTC components, and `gamestreaming_sdk.dll`.

The package also includes two large script payloads:

- a Hermes bytecode bundle used by the PC app interface; and
- an embedded web-client archive containing readable JavaScript for an alternate browser-based play implementation.

The web implementation was valuable for understanding field names and intended data flow, but the captured PC cloud launch used the native streaming SDK. This was confirmed because the live request contained the native SDK's predicted defaults and serialization shape, not the web client's defaults.

The active native path builds a cloud-play request with a settings object and adds a structured device-information header. It supplies application identity, SDK type, OS description, and hardware description from native caller-provided data. The captured baseline used the native SDK type and an otherwise generic/unknown play-body OS value. The full device header still described a Windows machine.

The embedded web path builds analogous information from browser user-agent data, user-agent client hints, native-host suffix fields, display dimensions, and device-pixel ratio. Its Xbox OS name is selected only when the browser identity itself matches an Xbox pattern. That makes the web code useful corroboration, but not proof that changing one string in the native path changes server authorization.

## Baseline cloud-streaming session

A normal cloud-enabled title was launched from the Xbox PC app with no request changes. The session completed through login, title discovery, session creation, connection setup, SDP/ICE negotiation, keepalive, and teardown. This established both a working capture method and a control for subsequent experiments.

The active client advertised itself as the native Microsoft Gaming app on Windows. Session creation was accepted. Media negotiation offered H.264 video profiles; no HEVC/H.265 or AV1 codec was present in the captured offer. The service did not return a distinct console or enhanced-quality class in the observed configuration response.

The package contains resolution aliases through 1440p and feature switches for decoder selection and HEVC preference. Those controls affect local media configuration and negotiation. The evidence does not connect them to the authenticated PC-versus-console identity decision.

## Cloud offering changes catalog membership

The PC cloud login normally selects the PC Game Pass offering. A one-variable experiment changed only the selected offering to the console cloud offering while leaving the device information and later requests unchanged.

The console offering was accepted. An immediate control run was used to reduce the chance that ordinary catalog churn explained the result:

| Catalog | Unique titles | GTA VI | Difference used as a control |
|---|---:|---|---|
| Normal PC offering | 2,827 | absent | baseline |
| Console offering | 2,828 | absent | one additional console-only classic title |

This is strong runtime evidence that offering selection affects cloud title discovery independently of the Windows client identity. It is not evidence that every console title is exposed, that the returned title can be launched, or that a missing title has been enabled for cloud streaming by Microsoft.

GTA VI was absent from both cloud catalogs observed during the test. A client-side identity change cannot launch a product for which the cloud service supplies no title record.

## Cloud session authorization remains independent

The additional console-only catalog title provided a useful control. The experiment retained the accepted console offering and substituted that title into an otherwise valid cloud-play request.

The request reached the cloud service but session creation was rejected with `DeviceTypeNotAllowed`. This proves that catalog membership and session authorization are separate checks.

Two follow-up A/B tests changed only self-reported client metadata:

1. The play-body OS name was changed to the Xbox value found in the shipped web client.
2. The play-body change was retained while existing device make, model, and OS header values were changed to generic Xbox-style values.

Both tests produced the same authorization rejection. The console offering itself continued to be accepted, so the failure was not caused by an invalid offering rewrite. These tests rule out the modified body OS and ordinary device-description header fields as sufficient authorization switches.

## Authenticated device classification

Credential-safe structural analysis explained why the cosmetic changes failed.

The token presented by the app to the cloud login is encrypted and authenticated. Its claims cannot be read or edited locally without the service's cryptographic key material. The cloud service then returns a separately signed token whose readable, non-personal claims include the selected offering and a device classification of `WindowsOneCore`.

That classification did not change when the request header was made to resemble an Xbox. The returned token is server-signed, so locally editing the device claim would invalidate its signature. This is the strongest observed cloud authorization signal.

The upstream authentication chain works at a higher trust level than ordinary request metadata:

1. Gaming Services obtains a signed device token.
2. That opaque device token is included when requesting an XSTS token.
3. The XSTS token is presented during cloud login.
4. The cloud service issues a signed token that carries the resulting device classification.
5. Cloud session creation uses that authenticated context when enforcing device eligibility.

This chain is why changing a JSON body or self-asserted device header does not turn a Windows client into an authenticated console.

## Device-authentication builder findings

Static analysis of the installed Gaming Services library recovered two mutually exclusive device-authentication request branches.

The proof-of-possession branch can serialize an explicit `DeviceType`, version, and optional serial number. Its concrete Windows provider supplies `Win32` for `DeviceType`. The recovered normal RPS-ticket construction path, however, requires a non-empty RPS ticket and takes the other branch. That branch includes the RPS authentication data and version but does not serialize `DeviceType` or serial number. Both paths may add model, SKU, and a proof key.

The proof key is an ECDSA P-256 JSON Web Key. It proves possession of a corresponding private key; it does not itself contain a PC-versus-console claim. The model and SKU values come from standard Windows system information. A separate `WindowsOneCore` literal found in the binary belongs to a platform serializer, not the explicit proof-of-possession `DeviceType` getter.

These findings narrow, but do not fully solve, the identity question. The normal recovered route does not simply send `DeviceType=WindowsOneCore` in cleartext. The remaining classification may depend on the signed RPS/device-token context, service-side knowledge, application identity, or another indirect path not observed in the capture. A real console device-authentication sample would be required to compare accepted console credentials and attestation semantics.

## PC store search and catalog pipeline

The store investigation used GTA VI as a public example because its catalog metadata identifies it as a console product and the Xbox PC app did not return it in search.

The public Microsoft catalog exposed a purchasable preorder availability restricted to the Xbox platform. It also exposed non-purchase/detail availability used to describe the product. This distinction predicted an important result: the PC app could potentially render public product content even when PC purchase or installation actions were unavailable.

Initial interception attempts also clarified the app's networking behavior. The visible Xbox process did not use the expected per-user proxy routes for this traffic. Process-scoped hostname observation showed that the app used one service for PC search and another for downstream list/detail hydration. A machine-trusted test certificate was needed for the specific native HTTP stack during the bounded capture; the temporary certificate was removed and verified absent afterward.

The downstream catalog service received PC-oriented list and hydration calls, but it never received the GTA VI product ID or the literal typed search query. Therefore it was not the component converting text into candidate products. The target had already been filtered out upstream.

The upstream PC search service returned structured results containing:

- arrays of product IDs grouped by category;
- product summaries keyed by product ID; and
- price records keyed by product ID.

The GTA VI product was absent from all three correlated structures. The request did not contain a simple console-model toggle. Instead, the strongest platform selector was the PC-specific service namespace and the PC/handheld availability data returned by that service.

## Server-side filtering and successful UI injection

A one-shot hydration probe appended the missing public product ID to an otherwise valid request. The service returned the original products but deliberately omitted the added target from both the summary and price dictionaries. This is strong runtime evidence that PC eligibility is enforced by the PC service, not only by a local search filter.

The next experiment supplied a complete, schema-compatible local response entry. It made the three required correlated edits:

- added the product ID to the games result list;
- added a matching product summary; and
- added matching price metadata.

That injection succeeded. The Xbox PC app displayed a GTA VI search tile. Selecting it opened the real Microsoft product page with authentic title text, artwork, videos, ratings, description, and bundle information.

This proves that the Windows app is technically capable of navigating to and rendering a console-only product once search omission is bypassed. It does not prove PC compatibility, purchase eligibility, entitlement, cloud availability, or stream authorization.

## Product-page and commerce gates

Opening the page revealed the next layer of server filtering. The PC-specific product-detail layout endpoints returned not-found responses for the target. The PC actions endpoint returned successfully but with no product or SKU actions. The entitlement lookup returned no entitlement. The rendered page accurately indicated that the game was not installable on PC and offered only a route to the supported store experience.

A narrowly scoped experiment changed the product-detail and action requests' device-family value from desktop Windows to Xbox. The same not-found and empty-action results were returned, and the page did not change. This was repeated during the same controlled session.

The result rules out the device-family query parameter as a standalone platform switch. The PC service namespace and server-side product policy remain authoritative for those details and commerce actions. Static inspection found no packaged console-commerce counterpart that the PC app could simply select.

The useful conclusion is that manufacturing a purchase button inside the PC app would not establish anything about cloud play. The supported store route and the cloud authorization path are separate systems.

## What has been disproved

The project has ruled out several attractive but incomplete explanations:

- Changing only the cloud play body's OS name does not grant console eligibility.
- Changing ordinary device make, model, and OS header values does not grant console eligibility.
- Changing only a store request's device-family query does not unlock console product actions.
- Rewriting a downstream public catalog availability does not create a search result when the upstream search service omitted the product.
- Adding a console-only product ID to the PC hydration request does not make the service return its metadata.
- The Windows deployment target in the app manifest is not shown to control cloud session identity.
- A visible product page is not evidence of purchase, entitlement, cloud catalog membership, or streaming authorization.
- A title appearing in the console cloud offering is not evidence that a Windows-authenticated device may launch it.

## What remains unknown

The following questions are still open:

- Which exact signed inputs or service-side records cause the cloud token issuer to classify the PC client as `WindowsOneCore`?
- What device-authentication fields, credentials, attestation, or application identity does an actual Xbox console present?
- Does any indirect Gaming Services construction path reach the explicit proof-of-possession branch in normal operation?
- How does the service weigh application identity, device token, model/SKU data, and proof-of-possession state when authorizing cloud play?
- Would a genuinely authorized console-class client receive different codec, bitrate, resolution, or streaming-policy negotiation?
- When Microsoft publishes a cloud record for a currently absent product, which offering and device classes will be allowed to launch it?

Without a credential-safe capture from a real console or authoritative service documentation, asserting exact accepted console field values would be guesswork.

## Current conclusion

The Xbox PC app is not separated from console behavior by one editable identity string. The project found a layered, service-enforced design:

1. PC search determines which store candidates are returned.
2. PC product services determine which details and actions are available.
3. Cloud offering selection determines which streaming titles are listed.
4. Signed authentication state determines whether the device may actually create a cloud session for a title.

Client-side response injection can prove UI and navigation capabilities. Offering substitution can prove catalog differences. Neither changes the authenticated device class. The most important unresolved work is therefore not another cosmetic header spoof; it is understanding the signed device-token chain and comparing it, safely and lawfully, with a genuine console authentication flow.

## Reproducibility and validation status

The repository includes the credential-safe experiment modules used to test the main hypotheses and focused unit tests built entirely from synthetic fixtures. It intentionally excludes raw captures, authentication material, certificate files, copied vendor binaries, machine state, and personal environment data.

The complete test suite passes:

```text
Ran 39 tests
OK
```

The live conclusions are supported by controlled A/B comparisons, successful baseline streaming, exact server responses, and agreement between runtime behavior and static request construction. Negative static searches are treated as bounded evidence rather than proof of absence. Raw capture files are intentionally not suitable for publication because they may contain authorization material; only sanitized summaries and analyzers should be shared.

### Running the tests

Python 3.13 is the validated version.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
$env:PYTHONPATH = "experiments"
.\.venv\Scripts\python -m unittest discover -s tests -p "test_*.py" -v
```

The experiment modules are provided to document exact test boundaries and make the findings reviewable. They are not a supported product or an authorization bypass. Do not run live interception experiments against accounts, devices, or traffic you do not own or have permission to test.
