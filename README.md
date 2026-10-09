# sample-trace-decision

A small, dependency-free Python library that makes a deterministic keep-or-drop decision for a trace id. Given the same trace id and the same rate, every call returns the same answer, so independent services can agree on which traces to record without talking to each other.

## Usage

```python
from sample_trace_decision import TraceDecisionSampler

sampler = TraceDecisionSampler(rate=0.1)

decision = sampler.decide("4bf92f3577b34da1")
print(decision.keep)      # True or False, deterministically
print(decision.trace_id)  # "4bf92f3577b34da1"
print(decision.rate)      # 0.1

# Or just the boolean:
if sampler.should_keep("4bf92f3577b34da1"):
    ...
```

`TraceDecisionSampler(rate)` exposes `.decide(trace_id) -> SamplingDecision` and `.should_keep(trace_id) -> bool`. `SamplingDecision` is a frozen dataclass with `trace_id`, `rate`, and `keep`.

## Why

Distributed tracing systems sample: they cannot record every trace, and they need every service along a request path to agree on whether a given trace is being kept, or the trace will be a broken, partial story. Random per-service decisions do not work; a deterministic hash of the trace id does.

The trade-off here is simplicity over sophistication. There is no dynamic rate adjustment, no priority sampling, and no per-service override. The rate is a single number in `[0, 1]`, interpreted as the fraction of traces to keep. If you need adaptive sampling, this is the wrong library; if you need a correct, boring, shared decision, it is the right one.

## The awkward edge

The rate is validated at decision time, not construction time. A `TraceDecisionSampler` object is mutable in its `rate` attribute on purpose, so a long-lived process can reconfigure sampling without rebuilding the object. The cost is that a bad rate (negative, above 1, NaN, or non-numeric) is only caught when `decide` runs. If you set `sampler.rate` to something invalid and never call `decide`, nothing will complain. Validate configuration at your configuration boundary if that matters to you.

`trace_id` may be a string, an integer, or bytes. `None` is rejected, because `str(None)` is `"None"`, which would silently turn a missing trace id into a real-looking one. An empty string is accepted and hashes normally; if your system uses empty ids as a sentinel, filter them yourself before calling `decide`.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

