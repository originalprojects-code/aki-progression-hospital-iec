# Online release instructions — v1.1.0-submission

Do not alter the science-locked A20 manuscript or Online Resource except for a later repository/DOI locator-only update if required.

Target GitHub repository: `originalprojects-code/aki-progression-hospital-iec`

Existing authoritative archive to preserve:
- GitHub main commit before release: `2f4fabd115e9f882e7deb4ae1f198a5fd3735734`
- existing tag/version: `v1.0.0-manuscript`
- existing Zenodo record/version: `1.0.0-manuscript`, DOI `10.5281/zenodo.21824202`

Required actions:
1. Verify no patient-level data, raw predictions, raw hospital-ID mappings, credentials, local Windows paths, or DUA-restricted derivatives are in the release package.
2. Update GitHub with the supplied metadata and portable submission-stage analysis scripts. Preserve all old history and the old tag.
3. Commit message: `Prepare v1.1.0-submission reproducibility snapshot`.
4. Create tag/release `v1.1.0-submission` after confirming main is clean.
5. Create a new Zenodo version corresponding to that GitHub release; do not overwrite the previous version. Suggested label: `1.1.0-submission` and description `Submission-ready reproducibility snapshot`.
6. Record the new GitHub commit, tag/release URL, Zenodo version DOI, and concept DOI if shown.
7. After the new DOI/version exists, compare it with the A20 Code Availability statement. If the exact DOI/version locator changed, create a locator-only A21 manuscript revision; do not change scientific prose.
8. Re-render any locator-only manuscript revision and verify all pages.

The public release package intentionally excludes raw patient-level data and private hospital identifier maps.
