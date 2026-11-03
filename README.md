# Recovery build 1.0.3

Add / refresh this repository in Homebrew Channel:

https://raw.githubusercontent.com/pacev93/stremio/homebrew/apps.json

Version 1.0.3 withdraws the cursor modification from 1.0.1/1.0.2 after a report of system-wide cursor suppression requiring a TV restart. All cursor/application platform code is restored byte-for-byte to upstream source. Only src/core/net.c differs under src/: the HTTP-206 connection reuse fix remains.

The original cursor may stay visible. The reported remote Play-key issue remains open; media-key handling is unchanged in this recovery build. Do not continue using 1.0.2. Install 1.0.3 as an update, without uninstalling.

Validation: ARM build, 12 transport scenarios, original permissions for all 330 data archive entries, original libraries/resources/licenses/app configuration, and no withdrawn cursor API names in the rebuilt executable. Actual TV behavior still needs verification.

The built-in updater still targets upstream. Source and investigation: https://github.com/pacev93/stremio/tree/7b705fa41fa0ca57c9447d07bf20e249aa4dedc2/docs/streaming-range-fix.md
