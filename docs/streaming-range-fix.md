# Origin test build: HTTP ranges and Magic Remote cursor

## Scope and source versions

Target: a rooted LG OLED77CX9LA, using Origin 1.0.0 with AIOStreams' native NNTP
engine, Easynews and Newznab indexers. The same setup reportedly works in the
current LG-store Stremio app and Nuvio. The TV is not reachable from this cloud
environment, so this is a test build, not a verified TV buffering cure.

The fork started at `051818e55cf38caed42d597fbcb05bdd3fc5bbd9`, which matched
[upstream Origin](https://github.com/stremio-origin/webos/tree/051818e55cf38caed42d597fbcb05bdd3fc5bbd9).
Origin's published release is 1.0.0. Its IPK SHA-256 is
`949d4eabafb7290258eae8ad9e405e7f8f31f4c030071039258f382ca7769a42`.

For official Stremio, the public
[web release v5.0.0-beta.43](https://github.com/Stremio/stremio-web/blob/v5.0.0-beta.43/package.json)
depends on `@stremio/stremio-video` 0.0.101, source commit
`fa1f32674159a0c0e2903cba44d4d41cd461e19f`. Both that package and the newer
0.0.103 were inspected after verifying npm archive integrity. The installed
LG-store binary and its bundled player version were not available; the public
web release is a source reference, not proof of the store app's exact version.

## Comparison before the change

| Area | Official public webOS player | Origin 1.0.0 |
| --- | --- | --- |
| Main direct video path | `WebOsVideo` assigns the URL to an HTML video element; webOS fetches and decodes it | Calls `com.webos.media/load` directly; webOS fetches and decodes it |
| Buffer configuration | No explicit `bufferControl` override in the inspected `WebOsVideo` | Explicit `userBufferCtrl:false` and `useSeekableRanges:true` |
| MKV metadata/subtitles | Uses platform tracks and optionally the bundled server's `/tracks` route; direct `withVideoParams` uses addon-provided hash/size/name | Own MKV worker reads the header, chapters, Cues and embedded subtitle blocks; missing indexes trigger scanning |
| Additional file reads | Depends on the bundled-server/player configuration; the inspected direct wrapper does not compute an OpenSubtitles file hash itself | Subtitle lookup may read the first and last 64 KiB for the hash; the MKV worker can harvest an entire selected indexed track |
| Unsupported audio | Platform/server dependent | Native converter reads 512 KiB / 2 MiB ranges through `NetRange`, then serves local HLS |

Relevant official sources:
[WebOsVideo](https://github.com/Stremio/stremio-video/blob/fa1f32674159a0c0e2903cba44d4d41cd461e19f/src/WebOsVideo/WebOsVideo.js),
[player selection](https://github.com/Stremio/stremio-video/blob/fa1f32674159a0c0e2903cba44d4d41cd461e19f/src/StremioVideo/selectVideoImplementation.js),
[direct video parameters](https://github.com/Stremio/stremio-video/blob/fa1f32674159a0c0e2903cba44d4d41cd461e19f/src/withVideoParams/withVideoParams.js).
Origin references: `src/platform/webos/video_webos.c:start_load`,
`src/core/mkvsubs.c:session_main,pick,scan_read`,
`src/core/subs.c:subs_os_hash` and `src/core/hproxy.c:rd_read`.

## Findings and limits

1. **Reproduced defect:** `range_data` returned zero when the last requested byte
   arrived, including for a correctly framed 206 response. libcurl interprets
   this as `CURLE_WRITE_ERROR`, discards the connection, and reconnects for the
   next range. The caller still sees `NR_OK` because it received bytes, masking
   the transport error. Four complete reads used four connections in the
   regression test. With the fix they use one, for both Content-Length and
   chunked 206 responses.
2. **Plausible additional contention:** Origin makes independent random-access
   MKV/subtitle/hash requests alongside playback. AIOStreams opens a byte stream
   for each HTTP request and uses a shared NNTP segment cache/pool. Extra distant
   reads can therefore compete with playback; they do not necessarily create a
   new NNTP session or discard all cached data. No backend traces from this
   user's deployment were available to quantify this effect.
3. **Separate native player limit:** The connection fix does not alter the HTTP
   fetcher inside LG's closed media service for ordinary direct playback.
   [Stremio issue #2771](https://github.com/Stremio/stremio-bugs/issues/2771)
   reports a high-bitrate native-fetch bottleneck on a different TV/webOS
   generation, with a proxy workaround. That report is consistent with a
   separate platform limit, but does not establish the cause on a CX.
   [Issue #2655](https://github.com/Stremio/stremio-bugs/issues/2655) concerns
   subtitle blinking/stuttering, not the same video-download defect.

AIOStreams reference inspected:
[`49cc6fa39af54a5bdb244d897cdf6008a7ebb594`](https://github.com/Viren070/AIOStreams/tree/49cc6fa39af54a5bdb244d897cdf6008a7ebb594),
particularly `packages/server/src/utils/range-stream.ts`,
`packages/core/src/usenet/integration/stream-session.ts` and
`packages/core/src/usenet/pool/segments-stream.ts`. This is the inspected source
version, not a verified version of the user's server.

## Narrow change and validation

For the streaming fix, only the production callback in `src/core/net.c` changes: a complete 206 is
acknowledged normally, enabling connection reuse. Responses exceeding the
requested buffer and a full-file 200 still stop at the existing limit.
This streaming fix adds no read-ahead proxy, new buffering service, subtitle
scheduling change, LG buffer setting or codec change. The same test package
also contains the separately requested cursor fix described below.

Run the transport regression using host SDL2 headers or the SDK headers:

```sh
source /workspace/stremio-env/activate.sh
python3 tests/net/run.py --sdl-include "$SDK/usr/include"
```

The test compiles the real `net.c` and uses a loopback HTTP/1.1 server. It failed
on the original callback (four connections instead of one), then passed all 12
scenarios after the fix: reuse with fixed/chunked framing, redirects, EOF,
ignored ranges, wrong offsets, interrupted and oversized responses, 429, 404,
and timeouts. Socket access is required for the local test server.
The ARM app build, existing log/crypto checks and both Dolby Vision tests also
passed. Existing compiler and package-metadata warnings were left unchanged.

## Test package and TV verification

The Homebrew test package uses the original app ID/title and version 1.0.1. Its
application payload is based on the verified upstream IPK: every file except
the rebuilt executable and `appinfo.json` is byte-for-byte unchanged. The latter
changes only its version. The original `libsbengine.so`, `libsbdts.so`, assets,
translations and licenses are retained. The original embedded Trakt/TMDB
configuration is retained without logging values; a plain public-source build
without that configuration would lose the built-in defaults.

On the CX, replay the same Easynews/NNTP MKV, same audio/subtitle selections and
same network connection before and after installation. Include a case with
AAC/AC3 and one requiring conversion, and compare playback progress versus wall
time, stalls and seek/resume. For diagnosis, compare backend request counts and
Origin's player/buffer diagnostics; redact stream URLs and tokens from logs.
Use the original 1.0.0 IPK to roll back if necessary. A TV comparison is still
required before calling the reported buffering problem fixed.

## Magic Remote cursor

The second requested fix addresses
[Origin issue #1](https://github.com/stremio-origin/webos/issues/1), reported on
the C8/C9 and now by the user on a CX: once visible, the pointer stays visible
throughout playback and elsewhere in the app.

Originally, `ptr_hide` only changed the internal hover state. It did not request
that the LG compositor hide its cursor. There was also no application-local idle
timeout, and `ptr_frame` returned immediately when hover input was not dirty.

The correction links pointer transitions to a small platform visibility API.
On webOS, `SDL_webOSCursorVisibility` is resolved from the already loaded system
SDL, with `SDL_ShowCursor` as the fallback if the export is absent or refuses the
request. No new hard dependency is introduced for older TVs. The macOS
implementation is a no-op, and the idle timeout is compiled only for webOS.

After three seconds without pointer activity, the cursor hides even during
playback and even without another mouse event. Real movement or a click brings
it back; arrows hide it immediately. Repeated system-show notices do not keep
it alive forever. Existing arrow/tremor suppression remains in place. A held
click is not timed out; releasing it starts a fresh idle period. Wheel activity
renews the visible pointer's deadline. No global TV setting is changed.

```sh
python3 tests/pointer/run.py
```

The tests compile the actual pointer-handler section and native wrapper from
the production files, with controlled time and stubbed UI/native calls. The
original handler fails the idle-hide assertion; the corrected handler passes
seven input scenarios and three native/fallback cases. The complete ARM build
also passes. The real LG compositor remains to be tested on the CX: show the
cursor, leave the remote still, verify it disappears after about three seconds,
then check movement, clicks, arrows, wheel input and a held click both in menus
and during playback. Autoscrolling mentioned separately in the upstream issue
is outside this change.
