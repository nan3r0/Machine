# Handoff: p2-seed-sources

## Goal
Seed `sources/` with at least 14 solved mysteries plus `sources/bloop.yaml` for the Phase 1 sample, every fact read from its https page, within the caps and content rules in the task notes and PLAN.md section 4.

## Status
done (owner review of every fact is still due in the PR)

## What changed
15 new files in `sources/`. Each fact was checked against the page through WebFetch and written in plain text by hand (no page text pasted, no links, no markup).

| File | Topic | Fact ids | Main source |
|---|---|---|---|
| bloop.yaml | The Bloop | 1-9 | https://oceanservice.noaa.gov/facts/bloop.html |
| sailing-stones.yaml | The sailing stones of Death Valley | 101-109 | https://en.wikipedia.org/wiki/Sailing_stones |
| perytons.yaml | Perytons at the Parkes radio telescope | 201-207 | https://en.wikipedia.org/wiki/Peryton_(astronomy) |
| blood-falls.yaml | Blood Falls in Antarctica | 301-307 | https://en.wikipedia.org/wiki/Blood_Falls |
| piltdown-man.yaml | Piltdown Man | 401-409 | https://en.wikipedia.org/wiki/Piltdown_Man |
| cottingley-fairies.yaml | The Cottingley Fairies photographs | 501-508 | https://en.wikipedia.org/wiki/Cottingley_Fairies |
| antikythera-mechanism.yaml | The Antikythera mechanism | 601-609 | https://en.wikipedia.org/wiki/Antikythera_mechanism |
| linear-b.yaml | The decipherment of Linear B | 701-707 | https://en.wikipedia.org/wiki/Linear_B |
| rosetta-stone.yaml | How the Rosetta Stone unlocked hieroglyphs | 801-807 | https://en.wikipedia.org/wiki/Rosetta_Stone |
| pioneer-anomaly.yaml | The Pioneer anomaly | 901-907 | https://en.wikipedia.org/wiki/Pioneer_anomaly |
| blc1.yaml | BLC1, the radio signal from the direction of Proxima Centauri | 1001-1008 | https://en.wikipedia.org/wiki/BLC1 |
| face-on-mars.yaml | The Face on Mars | 1101-1108 | https://en.wikipedia.org/wiki/Cydonia_(Mars) |
| clever-hans.yaml | Clever Hans, the counting horse | 1201-1208 | https://en.wikipedia.org/wiki/Clever_Hans |
| mechanical-turk.yaml | The Mechanical Turk chess machine | 1301-1308 | https://en.wikipedia.org/wiki/Mechanical_Turk |
| hubble-mirror.yaml | Why the Hubble Space Telescope sent blurry pictures | 1401-1408 | https://en.wikipedia.org/wiki/Hubble_Space_Telescope |

Bloop facts map to the sample scenes: 1-2 (1997, listening for volcanic activity in the southern Pacific), 3-4 (hydrophones over 3,219 km apart, the name), 5 (the guesses), 6 (PMEL hydrophones moving toward Antarctica), 7-8 (2005, icequake from an Antarctic glacier), 9 (about 95 percent of the ocean unexplored).

## Decisions made
- One source url per file (Wikipedia for 14 of them, NOAA for the Bloop). Wikipedia pages were the ones WebFetch read reliably and they cite the primary papers; the NASA Face on Mars page only had the 1976 caption, so Cydonia (Mars) is used instead.
- Hoaxes state only what is proven. Piltdown names Charles Dawson as the man who reported the find, never as the forger; the 2016 "one person" finding is stated without a name.
- Cottingley names Elsie Wright and Frances Griffiths: they are the publicly known subjects of a famous case from 1917 to 1983, not private individuals in the PLAN.md sense. Owner to confirm.
- First names were dropped wherever the page did not give them (Petroff, Turyshev, Freeth).
- Fact ids use blocks of 100 per file; the Bloop keeps 1-9 so the queued sample resolves.

## Tried and abandoned
- Altar Stone of Stonehenge: the 2024 Scottish origin was overturned by a 2026 study per the page, so the answer is disputed. Dropped.
- Betelgeuse Great Dimming: the page hedges the dust explanation ("may be the most likely"). Dropped as not settled enough.
- NASA "The Face on Mars" resource page: only the 1976 caption, no resolution. Replaced by Wikipedia.

## Known risks
- The Bloop page has no "eight years"; scene 4 of the sample says "the answer took eight years to find", which is derived from 1997 and 2005 (facts 1 and 7) but scene 4 only cites fact 6. A later exact-number check may flag it. The queue is outside this task's paths.
- Sample scene 7 says "loud enough to be heard across the Pacific" and cites facts 8 and 9; that support is in fact 3. Same note.
- WebFetch summarises pages through a small model, so a few facts are paraphrases of quoted sentences. The owner should spot-check numbers against the pages.
- Wikipedia text can change; facts were read on 2026-11-16.

## Next step
Owner reviews every fact in the PR. Consider whether the sample's scenes 4 and 7 should cite facts 1, 7 and 3 (owner or test_author, queue is locked to this task).

## Docs
none

## Evidence
- `LOOM_TASK=p2-seed-sources .venv/Scripts/python.exe -m pytest -q --tb=short tests/test_sources_files.py tests/test_queue_scripts.py`: 7 passed, 2 skipped (test_queue_scripts skips until p2-validate is done).
- `.venv/Scripts/python.exe -m pytest -q`: 426 passed, 312 skipped.
- `.venv/Scripts/python.exe tests/docs_check.py`: docs check passed.
