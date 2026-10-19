from __future__ import annotations

import unittest
from datetime import date, timedelta

from pipeline import forecasting


class ForecastingTests(unittest.TestCase):
    def test_features_use_exact_prior_calendar_days_only(self) -> None:
        start = date(2020, 1, 1)
        rows = [
            forecasting.Observation(str(index), start + timedelta(days=index), 10.0 + index)
            for index in range(9)
        ]
        by_date = {row.observed_date: row for row in rows}
        target_date = start + timedelta(days=8)
        self.assertEqual(
            forecasting.feature_values(by_date, target_date),
            (17.0, 16.0, 11.0),
        )

        changed_future = list(rows)
        changed_future[8] = forecasting.Observation("changed-target", target_date, 9999.0)
        self.assertEqual(
            forecasting.feature_values(
                {row.observed_date: row for row in changed_future}, target_date
            ),
            (17.0, 16.0, 11.0),
        )

    def test_missing_exact_lag_excludes_model_example(self) -> None:
        start = date(2020, 1, 1)
        rows = [
            forecasting.Observation("1", start, None),
            forecasting.Observation("2", start + timedelta(days=1), 11.0),
            forecasting.Observation("3", start + timedelta(days=2), None),
            forecasting.Observation("4", start + timedelta(days=3), 13.0),
            forecasting.Observation("5", start + timedelta(days=4), 14.0),
            forecasting.Observation("6", start + timedelta(days=5), 15.0),
            forecasting.Observation("7", start + timedelta(days=6), 16.0),
            forecasting.Observation("8", start + timedelta(days=7), 17.0),
        ]
        by_date = {row.observed_date: row for row in rows}
        self.assertIsNone(
            forecasting.feature_values(by_date, start + timedelta(days=7))
        )

    def test_persistence_uses_latest_prior_valid_value_and_records_age(self) -> None:
        start = date(2020, 1, 1)
        rows = [
            forecasting.Observation("1", start, 10.0),
            forecasting.Observation("2", start + timedelta(days=1), None),
            forecasting.Observation("3", start + timedelta(days=2), 14.0),
        ]
        self.assertEqual(
            forecasting.persistence_input(rows, start + timedelta(days=2)),
            (10.0, start, 2),
        )
        self.assertEqual(
            forecasting.persistence_input(rows, start + timedelta(days=3)),
            (14.0, start + timedelta(days=2), 1),
        )
        self.assertIsNone(forecasting.persistence_input(rows, start))

    def test_linear_regression_recovers_fixed_relationship(self) -> None:
        examples = []
        origin = date(2018, 1, 1)
        for index, features in enumerate(
            ((1.0, 2.0), (2.0, 1.0), (3.0, 4.0), (4.0, 3.0), (5.0, 6.0))
        ):
            target = 5.0 + 2.0 * features[0] - 3.0 * features[1]
            examples.append((origin + timedelta(days=index), features, target))
        model = forecasting.fit_linear_model(examples, feature_lags_days=(1, 2))
        self.assertAlmostEqual(model.intercept, 5.0)
        self.assertAlmostEqual(model.coefficients[0], 2.0)
        self.assertAlmostEqual(model.coefficients[1], -3.0)

    def test_fit_rejects_validation_and_test_examples(self) -> None:
        with self.assertRaisesRegex(forecasting.ForecastingError, "training dates only"):
            forecasting.fit_linear_model(
                [(date(2023, 1, 1), (1.0,), 2.0)],
                feature_lags_days=(1,),
            )

    def test_metrics_and_validation_quantile_are_deterministic(self) -> None:
        result = forecasting.regression_metrics([1.0, 3.0], [2.0, 1.0])
        self.assertEqual(result["n"], 2)
        self.assertEqual(result["mae"], 1.5)
        self.assertAlmostEqual(result["rmse"], (2.5) ** 0.5)
        self.assertEqual(forecasting._quantile([-2.0, 0.0, 2.0], 0.5), 0.0)


if __name__ == "__main__":
    unittest.main()
