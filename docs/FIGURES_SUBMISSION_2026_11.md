# Submission figure reproduction draft

The 8 November 2026 figure build scripts and reference outputs are included alongside the earlier A25 artwork and builder. The submission manuscript and supplementary information are in `manuscript/submission_2026_11/`. The earlier A25 inventories describe the historical snapshot; `release/SHA256SUMS_2026_11.txt` covers the newly added files listed therein.

The two build scripts read the pre-existing aggregate files under `aggregate_outputs/`, `analyses/`, and `tables/`, and write PNG and PDF figures to a chosen output directory. They do not run the underlying clinical analyses.

From the repository root:

```sh
python code/build_main_figures_2026_11.py . /tmp/iun-figures
python code/build_supplementary_figures_2026_11.py . /tmp/iun-figures
python code/verify_submission_figures_2026_11.py /tmp/iun-figures figures/submission_2026_11
```

The figure reference files were checked against the 8 November submission package: all 15 reference PDFs rendered identically, and the three reference main PNGs matched the Word image bytes. The 12 supplementary reference PNGs matched the supplementary source Word images. All 21 input CSVs had the same Git blob hashes as tag `v1.2.1-submission`.

The build scripts ran in a separate Linux environment using DejaVu Sans as a fallback because Arial was unavailable. This changes figure appearance; the verifier intentionally reports nonidentical files rather than asserting exact reproducibility in a different environment. A matching Windows/Arial environment is required to evaluate the stated byte-identical PNG reproduction. The standalone PDF files contain metadata such as timestamps, so the verifier compares their rendered pages at 150 dpi.

Research data and patient-level derivatives must not be added to the repository.
