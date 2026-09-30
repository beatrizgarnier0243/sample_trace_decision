import math
import unittest

from sample_trace_decision import TraceDecisionSampler, SamplingDecision


class TestSamplingDecisionType(unittest.TestCase):
    def test_is_frozen_dataclass(self):
        decision = SamplingDecision(trace_id="abc", rate=0.5, keep=True)
        with self.assertRaises(Exception):
            decision.keep = False


class TestDecide(unittest.TestCase):
    def test_returns_sampling_decision_with_expected_fields(self):
        sampler = TraceDecisionSampler(rate=0.5)
        decision = sampler.decide("trace-123")
        self.assertIsInstance(decision, SamplingDecision)
        self.assertEqual(decision.trace_id, "trace-123")
        self.assertEqual(decision.rate, 0.5)
        self.assertIsInstance(decision.keep, bool)

    def test_rate_zero_always_drops(self):
        sampler = TraceDecisionSampler(rate=0.0)
        for tid in ("a", "b", "c", "4bf92f3577b34da1", "0"):
            self.assertFalse(sampler.decide(tid).keep)

    def test_rate_one_always_keeps(self):
        sampler = TraceDecisionSampler(rate=1.0)
        for tid in ("a", "b", "c", "4bf92f3577b34da1", "0"):
            self.assertTrue(sampler.decide(tid).keep)

    def test_decision_is_deterministic_across_calls(self):
        sampler = TraceDecisionSampler(rate=0.3)
        first = sampler.decide("repeated-trace")
        second = sampler.decide("repeated-trace")
        self.assertEqual(first, second)

    def test_decision_is_deterministic_across_instances(self):
        a = TraceDecisionSampler(rate=0.3)
        b = TraceDecisionSampler(rate=0.3)
        self.assertEqual(a.decide("trace-X"), b.decide("trace-X"))

    def test_distribution_is_roughly_correct_for_rate(self):
        rate = 0.25
        sampler = TraceDecisionSampler(rate=rate)
        kept = sum(
            1 for i in range(20_000) if sampler.decide(f"trace-{i}").keep
        )
        # Expect ~5000; allow generous tolerance because this is a hash test.
        self.assertLess(abs(kept - 5000), 400)

    def test_should_keep_matches_decide_keep(self):
        sampler = TraceDecisionSampler(rate=0.5)
        for tid in ("t1", "t2", "t3"):
            self.assertEqual(sampler.should_keep(tid), sampler.decide(tid).keep)

    def test_rate_is_float_in_decision(self):
        sampler = TraceDecisionSampler(rate=1)
        decision = sampler.decide("tid")
        self.assertIsInstance(decision.rate, float)
        self.assertEqual(decision.rate, 1.0)

    def test_trace_id_normalized_in_decision(self):
        sampler = TraceDecisionSampler(rate=1.0)
        self.assertEqual(sampler.decide(b"abcdef").trace_id, "abcdef")
        self.assertEqual(sampler.decide(12345).trace_id, "12345")
        self.assertEqual(sampler.decide("").trace_id, "")

    def test_decisions_partition_evenly_at_rate_one_half(self):
        sampler = TraceDecisionSampler(rate=0.5)
        kept = sum(1 for i in range(10_000) if sampler.decide(f"t-{i}").keep)
        self.assertLess(abs(kept - 5000), 300)

    def test_nan_rate_is_rejected(self):
        sampler = TraceDecisionSampler(rate=float("nan"))
        with self.assertRaises(ValueError):
            sampler.decide("tid")

    def test_rate_above_one_rejected(self):
        sampler = TraceDecisionSampler(rate=1.0001)
        with self.assertRaises(ValueError):
            sampler.decide("tid")

    def test_rate_below_zero_rejected(self):
        sampler = TraceDecisionSampler(rate=-0.0001)
        with self.assertRaises(ValueError):
            sampler.decide("tid")

    def test_none_trace_id_rejected(self):
        sampler = TraceDecisionSampler(rate=0.5)
        with self.assertRaises(TypeError):
            sampler.decide(None)

    def test_invalid_rate_type_rejected(self):
        sampler = TraceDecisionSampler(rate="0.5")
        with self.assertRaises(TypeError):
            sampler.decide("tid")

    def test_rate_mutable_on_sampler(self):
        sampler = TraceDecisionSampler(rate=0.0)
        self.assertFalse(sampler.decide("tid").keep)
        sampler.rate = 1.0
        self.assertTrue(sampler.decide("tid").keep)


if __name__ == "__main__":
    unittest.main()
