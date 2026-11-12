# Research: Atlas Windows destination boundaries (#95)

## Findings

- [HIGH | Primary] Legacy MAX_PATH is 260 including the terminating NUL. A file path of 259 visible characters fits; 260 does not. Directory creation additionally reserves 12 characters for an 8.3 filename. Source: [Microsoft, Maximum Path Length Limitation](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation), read 2026-11-12.
- [HIGH | Primary, local experiment] `CreateDirectoryA` on this Windows machine accepts a 247-character absolute directory path and rejects 248 and 259 with error 206 (`ERROR_FILENAME_EXCED_RANGE`). The ANSI entry point deliberately exercises legacy behavior independently of Python's long-path-aware manifest. Reproducible temporary-filesystem tests: `test_native_legacy_directory_creation_boundary` in `tools/atlas/tests/test_windows_path_policy.py`. No registry or studio-drive changes.
- [HIGH | Primary] Extended UNC syntax replaces `\\server\share` with `\\?\UNC\server\share`. The marker adds six characters, not four. Subtracting only four overcounts the ordinary UNC path by two. Source: Microsoft page above. Lexical tests exercise the filesystem adapter and native Windows Plan measurement without connecting to a share.
- [HIGH | Primary] The extended namespace disables normal path parsing. Exact trailing-space/dot names must not be shortened during length measurement or destination construction. Source: Microsoft page above; real Windows move tests verify exact directory entries and retained source bytes on refusal.

## Contradictions and hidden variables

- Microsoft's prose says a directory name cannot exceed MAX_PATH minus 12. The native legacy creation test establishes the exclusive boundary used here: refuse at 248, allow 247. That creation boundary is not a claim that every Windows API rejects every existing directory of that length. Enumeration and rename have different constraints.
- LongPathsEnabled plus an application's longPathAware manifest changes native behavior. Atlas must not use that variability as permission to add a prefix to a destination beyond its legacy policy.
- ADR 0006's original "never refuses, never prefixes writes" predates exact trailing-space/dot support. Ordinary conform destinations still remain unprefixed, leaving the operating system to decide. Exact-name and already-prefixed destinations require explicit checks: files below 260, directory destinations below 248. Directory destination checks conservatively use the creation boundary for rename and merge too; they do not claim a separate native rename limit. An existing parent is not a directory creation: file moves into an exact-name 248-unit parent (254-unit file target), including inverse Plans, remain valid. Only missing parents pass through the creation check.
- The general Path Length Warning remains the longest resulting path, now warning at **260 or more**, not strictly above 260. It is not a guarantee that every shorter operation succeeds: directory creation, individual component limits, permissions, and filesystem behavior can still refuse it. The stricter directory destination check is not a change to the Deep Pass's existing-directory enumeration finding.

## Survivorship-bias sweep

- [HIGH | Primary] Microsoft's migration guidance documents opt-in long paths and warns that the shell and filesystem have different requirements. This rules out silently adopting the extended namespace for all Atlas writes. No abandonment evidence is needed to override the accepted ADR; the first-party compatibility caveat supports retaining it.

## Implementation scope

Use the existing `long_path` adapter for reads, source paths and stale-partial cleanup. A small shared display-path length calculation removes device markers without trimming filenames. On Windows legacy-boundary path measurements use UTF-16 code units, including subtree tails, archive previews, deep-scan reporting and read-prefix selection; other platforms retain character counts. Native emoji regressions prove refusal at 248 directory / 260 file units and warnings at 260 even when Python's character count is one less. Do not build a new filesystem abstraction or globally enable Windows long paths; no external component is needed for this lexical calculation.

Cleanup enumerates an existing archive root through `long_path`, stats each candidate through it, and removes only stale matching partials. Fresh partials and other runs' files remain. Archive creation/publishing policy is unchanged; cleanup support for an existing long directory is not authority to create one.

## Validation queue

- Native boundary and exact-name tests execute on Windows; portable adapter tests cover UNC boundaries with injected Windows path semantics.
- No live SMB share, Google Drive mutation, registry change, or claim of all-filesystem compatibility. UNC normalization is lexical evidence, not network interoperability evidence.
