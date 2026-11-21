# Model card

Two models trained on EU contract award notices (TED, 2019-2022). Technical
details: [Phase 5 documentation](../docs/phases/PHASE_5_MACHINE_LEARNING.md).

## Single-bid risk model

| | |
|---|---|
| **Predicts** | Probability that an awarded lot in a competitive procedure receives only one offer |
| **Algorithm** | LightGBM binary classifier (1,215 trees, early stopping on 2021) |
| **Inputs** | Information available when a tender is advertised: country, buyer, contract type, procedure, sector, estimate, lots, buyer's earlier single-bid rate (180-day gap) |
| **Training data** | 1.29M lots published 2019-2020; validation 0.71M (2021); test 0.69M (2022) |
| **Test performance (2022)** | ROC-AUC 0.762 · PR-AUC 0.607 (random 0.309) · Brier 0.173 · lift 2.37x in the riskiest 10% |
| **Intended use** | Ranking tenders for review; prompting buyers to reconsider design choices (lots, deadline, procedure) that raise risk |
| **Not for** | Concluding that a buyer or supplier acted improperly; automated sanctions |

## Fair price model

| | |
|---|---|
| **Predicts** | Award value of a lot: expected value (50th percentile) and an 80% range (10th-90th) |
| **Algorithm** | Three LightGBM models with quantile loss; range widened by conformal calibration on 2021 |
| **Inputs** | As above, plus CPV group and the buyer's typical contract value; never the award itself |
| **Training data** | 1.0M priced lots 2019-2020 (plausible values, no framework agreements) |
| **Test performance (2022)** | Median error 40.8% overall, **25.9% when the buyer published a genuine estimate**, 79.4% without one · 80% range covers 78.5% of actual values |
| **Intended use** | Indicating the typical price range for a planned tender; flagging awards far outside it for review |
| **Not for** | Setting bid prices on its own; concluding that a contract was overpriced |

## Known limitations

- **Risk indicator, not proof.** Single bids and unusual prices have legitimate
  causes: niche markets, small contracts, urgent needs, data-entry errors.
- **Country and buyer effects dominate.** The single-bid model's strongest drivers
  are country and buyer history, so it partly reflects where and who rather than
  how a tender is designed. Users should compare buyers within a country.
- **Data quality.** Estimates equal to the award value in 13% of priced lots may
  have been filled in after the award; buyer identity relies on name matching.
- **No quantities.** Prices cannot be predicted precisely without them.
- **Drift.** Performance drops from 2021 to 2022 (single-bid ROC-AUC 0.794 to
  0.762; price range coverage needed recalibration). Models should be retrained
  and recalibrated on recent data before use.
- **Coverage.** EU tenders above the publication thresholds only; national
  below-threshold procurement is not included.
