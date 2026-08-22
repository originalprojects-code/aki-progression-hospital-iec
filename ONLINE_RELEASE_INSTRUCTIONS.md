# Online release instructions

The current repository state is aligned with the A25 submission-locked manuscript
and final publication figure set.

## Pre-release checks

Before creating the release:

1. Confirm `docs/REPRODUCIBILITY_CHECKLIST_A25.md` is complete.
2. Run:
   `python aggregate_outputs/publication_figures/verify_publication_sources.py`
3. Run:
   `python code/08_BUILD_PUBLICATION_FIGURES.py`
4. Confirm Fig. 1–3 and Fig. S1–S12 all rebuild successfully.
5. Confirm `docs/A25_FINAL_FIGURE_SOURCE_MAP.csv` points to existing repository files.
6. Confirm the SHA-256 manifests under `release/` match the repository snapshot.
7. Confirm no restricted patient-level or hospital-identifier data are present.

## GitHub release

Create a new immutable tag and release:

`v1.2.0-submission`

Do not modify historical tags or releases.

Use `RELEASE_NOTES_A25_REPRODUCIBILITY.md` as the release-note basis.

## Zenodo

Archive the new GitHub release as a new software version. The current `.zenodo.json`
is prepared for version `1.2.0-submission` and retains links to the prior archived
version and the software record.

After Zenodo assigns the new version DOI, record that DOI in the manuscript/repository
only where appropriate; do not replace the concept-record relationship with a
version-specific DOI unless required by the citation workflow.

## Final verification

Download the released repository archive and rerun the publication-source verifier
and figure builder from the downloaded archive before considering the online release
complete.
