from __future__ import annotations

import os
import unittest
import urllib.error
from datetime import datetime, timezone
from unittest.mock import patch

from pipeline import insight_agent, llm_explainer

NO_KEYS = {name: "" for name in ("LLM_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY")}


class LlmExplainerGuardrailTests(unittest.TestCase):
    def setUp(self) -> None:
        now = datetime(2026, 10, 20, tzinfo=timezone.utc)
        self.forecast = insight_agent.answer_question("How did the model perform on the test set?", now=now)
        self.unknown = insight_agent.answer_question("Which team won the football match?", now=now)
        self.model = self.forecast["evidence"][0]["values"]["model"]

    def test_not_configured_sends_nothing(self) -> None:
        with patch.dict(os.environ, NO_KEYS):
            self.assertEqual(llm_explainer.explain(self.forecast), {"used": False, "reason": "not_configured"})

    def test_non_evidence_tags_are_removed(self) -> None:
        text = f"The average error was {self.model['mae']:.2f} [E1] [LIMITATIONS]."
        out = llm_explainer.explain(self.forecast, call=lambda system, user: text)
        self.assertTrue(out["used"], out)
        self.assertNotIn("LIMITATIONS", out["text"])
        self.assertIn("[E1]", out["text"])

    def test_faithful_paraphrase_is_accepted(self) -> None:
        text = (
            f"On held-out days the model's average error was {self.model['mae']:.2f} µg/m³ of PM2.5, "
            f"slightly better than simply repeating yesterday's value [E1]. This is a historical backtest [E1]."
        )
        out = llm_explainer.explain(self.forecast, call=lambda system, user: text)
        self.assertTrue(out["used"], out)
        self.assertEqual(out["text"], text)

    def test_invented_number_is_rejected_and_falls_back(self) -> None:
        text = "The model is 37% more accurate than persistence [E1]."
        out = llm_explainer.explain(self.forecast, call=lambda system, user: text)
        self.assertFalse(out["used"])
        self.assertEqual(out["reason"], "rejected_by_guardrail")
        self.assertIn("unsupported_numbers:37", out["violations"][0])

    def test_abstention_must_be_preserved(self) -> None:
        bad = llm_explainer.explain(self.unknown, call=lambda s, u: "Pakistan probably won.")
        self.assertIn("missing_abstention", bad["violations"])
        good = llm_explainer.explain(
            self.unknown, call=lambda s, u: f"{insight_agent.ABSTENTION} The data only covers air quality."
        )
        self.assertTrue(good["used"], good)
        urdu = llm_explainer.explain(
            self.unknown,
            language="ur",
            call=lambda s, u: f"{insight_agent.ABSTENTION_UR} یہ سوال ہوا کے اعداد و شمار میں نہیں ہے۔",
        )
        self.assertTrue(urdu["used"], urdu)

    def test_citations_must_exist(self) -> None:
        count = len(self.forecast["evidence"])
        out = llm_explainer.explain(self.forecast, call=lambda s, u: f"See the report [E{count + 1}].")
        self.assertIn("citation_out_of_range", out["violations"])
        out = llm_explainer.explain(self.forecast, call=lambda s, u: "The model did well.")
        self.assertIn("no_citations", out["violations"])

    def test_urdu_digits_are_checked_like_western_digits(self) -> None:
        mae = f"{self.model['mae']:.2f}".translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
        ok = llm_explainer.explain(self.forecast, language="ur", call=lambda s, u: f"اوسط غلطی {mae} تھی [E1]")
        self.assertTrue(ok["used"], ok)
        bad = llm_explainer.explain(self.forecast, language="ur", call=lambda s, u: "بہتری ۳۷ فیصد [E1]")
        self.assertFalse(bad["used"])

    def test_provider_error_falls_back_without_raising(self) -> None:
        def failing(system: str, user: str) -> str:
            raise urllib.error.URLError("offline")

        out = llm_explainer.explain(self.forecast, call=failing)
        self.assertEqual(out["reason"], "provider_error:URLError")

    def test_prompt_contains_only_verified_answer_and_evidence(self) -> None:
        captured = {}

        def capture(system: str, user: str) -> str:
            captured["system"], captured["user"] = system, user
            return f"{self.model['mae']:.2f} [E1]"

        llm_explainer.explain(self.forecast, call=capture)
        self.assertIn("Use ONLY the facts", captured["system"])
        self.assertIn('"VERIFIED_ANSWER"', captured["user"])
        self.assertIn('"E1"', captured["user"])


if __name__ == "__main__":
    unittest.main()
