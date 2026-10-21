# First PAQI historical forecasting experiment

**Run date:** 2026-10-20  
**Data:** Pinned PAQI Zenodo version `10.5281/zenodo.15845428`; raw SHA-256 `2359a11850df9d5798c446e1013c09f22914426ffc1e1d928c2ec9824502debf`.  
**Experiment:** Date-ordered historical next-value prediction; no model tuning or selection on test data.

## Result summary

The fixed ordinary least-squares model **did beat persistence on the paired held-out test dates** by MAE and RMSE, with modest improvements. This is a measured result for the published PAQI series only. It is not evidence of statistical significance or a current/live forecast.

| Split | Method / comparison | n | MAE (µg/m³) | RMSE (µg/m³) | Model − persistence MAE / RMSE |
|---|---|---:|---:|---:|---:|
| Validation | Persistence, all eligible targets | 451 | 10.1084 | 16.7245 | — |
| Validation | Linear model | 451 | 9.8193 | 15.8990 | — |
| Validation | Paired, same 451 targets | 451 | — | — | −0.2891 / −0.8255 |
| Test | Persistence, all eligible targets | 446 | 10.2720 | 17.3474 | — |
| Test | Linear model | 436 | 9.9012 | 16.3265 | — |
| Test | Persistence on the model's same 436 targets | 436 | 10.1507 | 16.9419 | — |
| Test | Paired, same 436 targets | 436 | — | — | **−0.2495 / −0.6153** |

The 436-pair test improvement is about 2.5% in MAE relative to persistence on those same rows. No significance test was performed. The test-set result is a single chronological holdout and should be treated as descriptive, not as proof of generalization to a future period.

### Error by target year

Each comparison below uses the same target rows for model and matched persistence within that year. Differences are model minus persistence; negative favors the model.

| Split | Year | Paired n | Model MAE | Persistence MAE | Δ MAE | Model RMSE | Persistence RMSE | Δ RMSE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Validation | 2022 | 172 | 9.9472 | 10.0756 | −0.1284 | 14.5928 | 15.2730 | −0.6803 |
| Validation | 2023 | 279 | 9.7405 | 10.1287 | −0.3881 | 16.6533 | 17.5596 | −0.9064 |
| Test | 2023 | 72 | 17.1574 | 16.9764 | **+0.1810** | 25.1768 | 25.3306 | −0.1538 |
| Test | 2024 | 364 | 8.4659 | 8.8005 | −0.3347 | 13.9248 | 14.7270 | −0.8022 |

The model's test MAE is slightly worse than persistence for 2023's 72 paired targets, despite a slightly lower RMSE. The aggregate test MAE improvement is driven by the much larger 2024 subset. This variability argues against presenting the overall improvement as robust.

## Protocol and leakage controls

- Frozen splits: train 2016-10-06–2022-07-12; validation 2022-07-13–2023-10-06; test 2023-10-07–2024-12-31.
- Baseline: latest finite, nonnegative PM2.5 value on a strictly earlier observation date. Its date and age are retained per row. The test baseline used the immediately previous calendar day's value for 444 numeric targets and an older reading for two: 2023-12-17 used 2023-12-12 (age 5 days), and 2023-12-29 used 2023-12-26 (age 3 days). No numeric test target lacked a prior valid value.
- Model: ordinary least squares with an intercept and exact calendar-day PM2.5 lags 1, 2 and 7. The 2,099 complete training examples fall between 2016-10-13 and 2022-07-12; the first seven dates cannot supply all exact lags. No scaling or imputation is used. A model example is excluded if any required lag is absent/blank.
- The model specification was fixed; coefficients were fitted on training rows only. Validation was used for validation metrics and empirical residual interval calibration, not coefficient fitting. The test set was not used for model fitting, feature selection or tuning.
- The test has 446 numeric labels; 10 of those lack at least one exact model lag and are excluded from the model. The six blank target labels are never imputed or scored. The model and paired persistence comparison use the same 436 labeled dates.
- Rows for training dates in the prediction CSV contain in-sample fitted predictions, marked `training_in_sample_not_scored`; they are not evaluation metrics. Validation and test residuals use actual minus prediction.

**Timing caveat:** PAQI records contain dates, not measurement-release timestamps. All input features are from strictly earlier observation dates, but the dataset does not prove that each preceding-date 24-hour value was published and available before a real-world forecast cutoff. Therefore this is a leakage-controlled date-index backtest under the assumption that earlier-date values are available; it is not evidence of deployable next-day forecast latency.

## Empirical prediction-error interval

The linear model's signed validation residuals (actual minus prediction; n=451) have empirical 5th and 95th percentiles of **−23.7912** and **+29.5396 µg/m³**. Adding these residual quantiles to each test model prediction covered **399 of 436** actual test values (**91.51%**). This is a historical empirical interval calibrated only from validation residuals. It is not a guaranteed probabilistic interval, and the observed test coverage is descriptive.

## Limitations

- The target is the published PAQI Karachi series—not an identified monitor or representative citywide concentration. Station identity, monitor/network aggregation, exact timezone/window, QA, blank-value meaning and methodology changes remain unresolved; see [forecasting readiness](forecasting_readiness.md) and the [unsent PAQI inquiry](paqi_methodology_inquiry.md).
- The source endpoint is 2024-12-31. The experiment is entirely historical and provides no current conditions.
- The model uses only the PAQI series. The warehouse also holds the U.S. Consulate and Urban Unit sources (see README), which are not model inputs.
- Residuals and year groups are temporally dependent; no significance test was attempted.

## Reproduction and artifacts

From the repository root, first require a passing existing data pipeline, then run:

```powershell
python -m pipeline.forecasting
python -m unittest discover -s tests -v
```

The command validates existing raw/cleaned/gold lineage without redownloading or modifying the source data. It writes:

- `data/reports/forecast_metrics.json`
- `data/reports/forecast_predictions.csv`
- `data/reports/forecast_linear_model.json`

These generated files are ignored by Git. The model artifact records the training period, coefficients, source version and raw checksum. The metrics JSON is the complete machine-readable result; the CSV retains every gold row ID, date, split, target, predictions, residuals, lag values, persistence input age, and evaluation status.
