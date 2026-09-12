# Bundled Stockfish 19

These are the original, unmodified desktop archives from the official release:
https://github.com/official-stockfish/Stockfish/releases/tag/sf_19

`manifest.json` records the original asset URL and SHA-256 digest published by GitHub, as well as the executable's checksum and archive member name. The runtime selects the local archive; it never uses the URLs to download anything.

Each archive includes the executable, `Copying.txt` (GPL v3), `AUTHORS`, `src/`, its Makefile, scripts and upstream documentation. Keep the complete original archives when redistributing this skill. Source is available directly in these bundled archives; extract one normally to read or modify it and consult its README and compiling documentation. Preserve the upstream notices. Stockfish's own GPL permissions, including commercial use under its terms, remain unchanged.

Supported bundles: macOS universal (Apple Silicon/Intel), Windows x86-64/ARM64, Linux x86-64/ARM64. Other platforms require an explicit external UCI engine. Only the current machine's executable is unpacked for analysis; NNUE evaluation data is embedded in the upstream executables.

The archives are committed as ordinary Git files, not Git LFS pointers. They total about 406 MB; the installed cache adds approximately one executable for the current platform. No network access is needed to unpack or run the bundled engine.
