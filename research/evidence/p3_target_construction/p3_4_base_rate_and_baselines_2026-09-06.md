# P3.4 Development Base Rates and Baselines

**Status:** PASS_WITH_PERSISTENCE_AS_EX_POST_REFERENCE
**Scope:** development only; all reported accuracies are descriptive/in-sample

| Label | Count | Share |
|---|---:|---:|
| UP | 4,354 | 19.893996% |
| DOWN | 7,190 | 32.852052% |
| NEUTRAL | 10,342 | 47.253952% |

The majority baseline must be learned only from the training portion available
for each evaluation. Across the complete development sample, NEUTRAL is the
descriptive majority and represents `47.253952%`
of valid labels.

The frozen persistence formula is `y_hat_t = y_(t-1)`. It is computable on
`21,884` consecutive valid development pairs and has
a descriptive accuracy of `71.449461%`.
It is retained only as an ex-post reference because the source does not prove
that the preceding outcome was published by the decision cutoff.

The registered availability-safe supplement is an hour-of-week training
majority: learn a class separately for each Danish local weekday-hour from the
training segment and use the global training majority for unseen groups. Its
performance will be evaluated only inside later chronological splits.
