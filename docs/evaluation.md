# Small synthetic ranking experiment

The repository includes 25 fictional internship candidates and three student profiles. `docs/evaluation/proposed-labels.json` contains proposed relevance labels authored with the fixtures. `reviewed-labels.json` is deliberately empty until someone independently reviews the examples. Do not rename proposed labels as reviewed.

Run from `backend`:

```bash
python -m app.jobs.evaluate
python -m app.jobs.evaluate --labels ../docs/evaluation/reviewed-labels.json --output ../docs/evaluation/reviewed-results.json
```

The second command refuses to report results while the reviewed set is empty. There is no training or parameter tuning on this set; the fixed demonstration split and candidate corpus are identical for the embedding and keyword-overlap methods. The baseline ranks required-skill overlap divided by the number of required skills; ties use stable source IDs. The embedding method uses the same production text/chunk/normalization functions.

Actual CPU MiniLM run during implementation:

| Method | Mean Precision@5 | MRR |
| --- | ---: | ---: |
| Real MiniLM | 0.8000 | 1.0000 |
| Keyword baseline | 0.7333 | 1.0000 |

The full ranked IDs and per-profile results are in `evaluation/results.json`. **None of the three profiles produced a score strictly above 0.80** for this candidate set. The production UI therefore correctly displays an empty high-match state. Ranking evaluation here uses the entire ranked list rather than pretending filtered-empty recommendations contain five results.

These values are an implementation demonstration on three synthetic examples, not independently measured recommendation accuracy, statistical evidence of general superiority, or hiring probability. Precision@5 of 0.80 and a cosine cutoff of 0.80 are entirely different quantities; their coincidental values must not be conflated. MRR=1 only means the first returned candidate was in the proposed relevant set for each of these three profiles.

For a defensible academic evaluation, ask independent reviewers to label a larger held-out set before running it, record disagreements and relevance definitions, keep all ranking methods on the same candidates, report coverage at the chosen cutoff, and disclose false positives/negatives. Do not tune and evaluate on the same labels. No model was trained in this project.
