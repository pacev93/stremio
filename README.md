# Origin range and cursor test build

Add this repository to Homebrew Channel:

https://raw.githubusercontent.com/pacev93/stremio/homebrew/apps.json

Version 1.0.2 includes two changes over upstream 1.0.0: completed HTTP range connection reuse and webOS native cursor visibility with a 3-second idle timeout. Tests: 12 transport scenarios and 10 cursor scenarios, ARM build, existing crypto and Dolby Vision tests. TV playback/compositor behavior remains unverified.

Original libraries, resources, licenses and embedded app configuration are retained. The application payload changes only the rebuilt executable and package version. Same app ID; no prior uninstall is needed. The built-in updater is unchanged and still targets upstream. Rollback: reinstall original 1.0.0 IPK.

Source and analysis: https://github.com/pacev93/stremio/tree/0dff2cdeac8307208443f1bb02633044c980d961/docs/streaming-range-fix.md

## Startup correction in 1.0.2

The first 1.0.1 package incorrectly carried mode 0704 for the executable. Version 1.0.2 restores every package entry mode from the original upstream IPK (executable 0755). The application binary is unchanged from 1.0.1. Final-archive permission checks reject 1.0.1 and pass 1.0.2. Actual TV startup still requires confirmation. Update through the same repository without uninstalling.

Current source: https://github.com/pacev93/stremio/tree/f6111a387e89dce8c4fe1709bf0601b68ed2b89b/docs/streaming-range-fix.md
