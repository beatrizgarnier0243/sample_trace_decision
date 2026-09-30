from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class SamplingDecision:
    """Result of a sampling decision for a single trace.

    Attributes:
        trace_id: The trace identifier that was evaluated.
        rate: The sampling rate in [0, 1] that produced this decision.
        keep: True if the trace should be retained, False if it should be dropped.
    """
    trace_id: str
    rate: float
    keep: bool


class TraceDecisionSampler:
    """Deterministic per-trace sampler.

    The same trace_id always yields the same decision for a given rate, because
    the decision is derived from a stable hash of the trace_id rather than from
    randomness or time. This lets every service in a distributed system agree
    on whether to keep a given trace without coordinating.

    The hash is SHA-256 truncated to 8 bytes. SHA-1 is deliberately avoided
    because it is cryptographically broken; even for non-security use, using
    it invites audits and tooling complaints that add no value. SHA-256 is in
    every supported Python's hashlib and costs us nothing here.

    The rate is interpreted as "fraction of traces to keep." A rate of 0.0
    drops everything; 1.0 keeps everything. Values outside [0, 1] raise
    ValueError at decision time rather than at construction time, so a single
    misconfigured rate does not poison a long-lived sampler object whose rate
    is updated later.
    """

    _HASH_TRUNCATE_BYTES = 8
    _HASH_DIVISOR = 2 ** (_HASH_TRUNCATE_BYTES * 8)

    def __init__(self, rate: float = 1.0):
        self.rate = rate

    @staticmethod
    def _normalize_trace_id(trace_id: object) -> str:
        """Coerce a trace_id to its string form.

        Distributed-trace systems commonly represent trace ids as hex strings,
        but integers and bytes also appear. We stringify rather than reject so
        that callers do not have to remember the exact type for every backend.
        None is rejected explicitly because str(None) == 'None' would silently
        make a non-trace look like a real trace.
        """
        if trace_id is None:
            raise TypeError("trace_id must not be None")
        if isinstance(trace_id, bytes):
            return trace_id.decode("utf-8")
        return str(trace_id)

    @classmethod
    def _hash_fraction(cls, trace_id_str: str) -> float:
        """Map a trace_id string to a deterministic float in [0, 1)."""
        digest = hashlib.sha256(trace_id_str.encode("utf-8")).digest()
        truncated = int.from_bytes(digest[: cls._HASH_TRUNCATE_BYTES], "big")
        return truncated / cls._HASH_DIVISOR

    def _validate_rate(self) -> None:
        if not isinstance(self.rate, float) and not isinstance(self.rate, int):
            raise TypeError(
                f"rate must be a float, got {type(self.rate).__name__}"
            )
        if self.rate < 0.0 or self.rate > 1.0 or _is_nan(self.rate):
            raise ValueError(f"rate must be in [0, 1], got {self.rate!r}")

    def decide(self, trace_id: object) -> SamplingDecision:
        """Return a SamplingDecision for trace_id at the configured rate."""
        self._validate_rate()
        normalized = self._normalize_trace_id(trace_id)
        fraction = self._hash_fraction(normalized)
        keep = fraction < float(self.rate)
        return SamplingDecision(trace_id=normalized, rate=float(self.rate), keep=keep)

    def should_keep(self, trace_id: object) -> bool:
        """Convenience: return only the boolean decision."""
        return self.decide(trace_id).keep


def _is_nan(value: float) -> bool:
    """Return True if value is NaN, defined per the IEEE 754 rule.

    The idiomatic `value != value` test is used because math.isnan raises
    TypeError on non-float inputs; we only call this after confirming a
    numeric type, and `!=` stays correct if Python's numeric tower ever
    hands us something exotic.
    """
    return value != value
