# Origin range and cursor test build

Add this repository to Homebrew Channel:

https://raw.githubusercontent.com/pacev93/stremio/homebrew/apps.json

Version 1.0.1 includes two changes over upstream 1.0.0: completed HTTP range connection reuse and webOS native cursor visibility with a 3-second idle timeout. Tests: 12 transport scenarios and 10 cursor scenarios, ARM build, existing crypto and Dolby Vision tests. TV playback/compositor behavior remains unverified.

Original libraries, resources, licenses and embedded app configuration are retained. The application payload changes only the rebuilt executable and package version. Same app ID; no prior uninstall is needed. The built-in updater is unchanged and still targets upstream. Rollback: reinstall original 1.0.0 IPK.

Source and analysis: https://github.com/pacev93/stremio/tree/0dff2cdeac8307208443f1bb02633044c980d961/docs/streaming-range-fix.md
