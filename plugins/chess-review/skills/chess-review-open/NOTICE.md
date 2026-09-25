# Licensing and dependencies

This skill's own scripts, HTML templates, documentation and fictional examples are released under the PolyForm Noncommercial License 1.0.0. See LICENSE. Anyone may use, copy, modify and share them free of charge for noncommercial purposes (personal study, hobby projects, teaching, charities, schools, public research bodies and government institutions). Commercial use needs separate written permission from the copyright holder. This is a source-available noncommercial license, not an OSI-approved open source license.

Required Notice: Copyright 2026 Mission Nine Lab Inc. (https://github.com/kevina0817-ctrl/chess-review-skill)

Third-party components keep their own licenses. The noncommercial restriction above applies only to this project's own files, never to these components:

- Stockfish 19, by the Stockfish developers: GPL-3.0. Bundled as five unmodified official desktop distribution archives under `vendor/stockfish/`, each including upstream source, build scripts, AUTHORS and the GPL license text (Copying.txt). The skill starts Stockfish as a separate process and talks to it only over the UCI protocol; it does not link against or modify it. See `vendor/stockfish/README.md` and `manifest.json` for exact origins and checksums. https://stockfishchess.org/download/ · https://github.com/official-stockfish/Stockfish
- python-chess (`chess` on PyPI), by Niklas Fiekas and contributors: GPL-3.0-or-later. Installed separately by the user with pip; not redistributed here. https://python-chess.readthedocs.io/en/latest/#license
- Chess piece SVG artwork by Colin M. L. Burnett, distributed through python-chess under GPL-3.0-or-later and embedded in generated review pages at build time. Preserve the attribution line in generated pages. https://github.com/niklasf/python-chess/blob/master/chess/svg.py
- Lichess chess-openings: CC0-1.0, revision `c67912be581f0793dbaa776be5ccf111e01f88d9`. `assets/openings.json` derives position identifiers from the upstream a–e TSV move sequences using python-chess. Full license: `assets/openings-COPYING.txt`. https://github.com/lichess-org/chess-openings
- Single-move metric formulas are credited to https://lichess.org/page/accuracy. This project implements its own arithmetic game mean and event thresholds; it does not claim to reproduce Lichess game accuracy.
- Playwright, by Microsoft: Apache-2.0. Optional browser-testing dependency, installed separately. https://github.com/microsoft/playwright

The white/black example PGNs use fictional participant names. The Opera Game example is a sourced public historical teaching game, not a user record; its coaching text is original. This repository contains no personal review archive or hosting configuration.
