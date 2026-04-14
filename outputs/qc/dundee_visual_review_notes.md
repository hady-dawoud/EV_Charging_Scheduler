# Dundee Visual Review Notes

## Late-October Check

- Late-October raw daily energy dip present: No
- Late-October reconstructed filtered energy dip present: Yes
- Raw late-October median / nearby baseline median: 1.030x
- Reconstructed late-October median / nearby baseline median: 0.158x

## Interpretation

- The late-October drop appears to be a preprocessing artifact rather than a real demand collapse.
- Raw arrival-date energy remains normal in the late-October window, while reconstructed filtered energy falls sharply.
- In the same window, 2,026 of 2,439 clean rows have missing or nonpositive `session_minutes`, so they are excluded from the filtered reconstruction.

## Recommendation

- Use the raw daily delivered energy chart in the presentation when discussing real-world daily demand behavior.
- Use the reconstructed filtered daily series only as a modeling-diagnostic chart, with an explicit caveat that it is sensitive to QC exclusions and duration quality.

## Note on Yearly Charts

- The yearly charts were not regenerated in this step.
- If the existing yearly charts are reused in slides, annotate them with: `2021 = Jul-Dec` and `2025 = Jan-Aug`.
