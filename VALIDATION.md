# Validation record

Validated on 27 October 2026 using the local project virtual environment.

- All 10 deterministic unittest cases passed.
- Complete pipeline finished successfully on saved Yahoo Finance data.
- All strategy runs asserted nonnegative cash and reconciled completed trade P&L
  to final equity less starting capital (including sensitivity and cost checks).
- CSV snapshot SHA-256 hashes matched data/manifest.json.
- Technical_Report.pdf contains 10 pages, rendered and visually checked.
- Actual runtime versions are in results/configuration.json.
- This validation verifies implementation behavior; it does not establish
  financial profitability or statistical significance.

The local .venv uses the Codex bundled Python runtime and its existing pandas and
ReportLab packages. It is machine-specific and excluded from the submission ZIP.
Use README's fresh-setup instructions to reproduce on another computer.
