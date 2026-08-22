# A25 publication figure reproducibility

The final publication chain is:

`restricted source data -> aggregate analysis outputs -> disclosure-safe publication sources -> code/08_BUILD_PUBLICATION_FIGURES.py -> Fig. 1–3 and Fig. S1–S12`

All 15 final A25 figures are provided under `figures/` as 600-dpi PNG and vector PDF.

A clean-room rebuild was completed without external cloud-storage services, query services, patient-level rows, row-level predictions, or row-level SHAP files: **15/15 PASS**.

See `A25_FINAL_FIGURE_SOURCE_MAP.csv` for figure-level provenance.

## Disclosure boundary

The public publication-source layer contains only aggregate or anonymous numerical coordinates needed to regenerate artwork. It contains no patient identifiers, patient-level rows, hospital identifiers, hashed hospital identifiers, credentials, or raw hospital mappings.

## Rebuild

```bash
python code/08_BUILD_PUBLICATION_FIGURES.py
```

Minor byte-level differences can occur across systems because of font rasterization or plotting backends. The reproducibility target is numerical identity, panel/label identity, publication geometry, and 600-dpi/vector output availability.
