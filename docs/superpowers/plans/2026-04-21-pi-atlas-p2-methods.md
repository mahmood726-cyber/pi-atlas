"""Plan 2: Implement remaining PI methods.

Methods to implement (as per Protocol):
2. HTS + REML
3. HTS + PM (Paule-Mandel)
4. HKSJ-adjusted
5. Partlett-Riley (R metafor wrapper)
6. Nagashima-Noma (R pimeta via subprocess or Python port)
7. Bayesian posterior predictive (R bayesmeta wrapper)
8. Bayesian + MAP prior (Leveraging MAPriors)
9. Non-parametric cluster bootstrap
10. HTS + SJ (Sidik-Jonkman)

We will start with methods 2, 3, 4, and 10 as they are relatively straightforward extensions/adjustments to the standard HTS approach and can be written in pure Python.
"""
