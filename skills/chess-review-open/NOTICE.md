# Licensing and dependencies

This skill's scripts, templates and documentation are released under GPL-3.0-or-later. See LICENSE.

- python-chess (`chess` on PyPI), by Niklas Fiekas and contributors: GPL-3.0-or-later. Installed separately. https://python-chess.readthedocs.io/en/latest/#license
- The generated piece SVG artwork comes from python-chess and credits Colin M. L. Burnett under GPL-3.0-or-later. Preserve the attribution in generated pages. https://github.com/niklasf/python-chess/blob/master/chess/svg.py
- Stockfish 19 is bundled as five unmodified official desktop distribution archives under `vendor/stockfish/`, invoked through UCI. Every archive includes upstream source, build scripts, authorship and GPL license files. See `vendor/stockfish/README.md` and `manifest.json` for exact origins and checksums. https://stockfishchess.org/download/
- Playwright is an optional browser-testing dependency, installed separately. https://github.com/microsoft/playwright

The example PGNs use fictional participant names and are teaching sequences, not personal game records. This repository contains no personal review archive or hosting configuration.
