"""Task-keyed random streams.

SEAKMC drew every dimer direction and every KMC selection from the unseeded
global NumPy generator, so no run could be reproduced and no regression test
could exist.

The obvious repair -- seed the global generator once per process -- is worse
than it looks, and measurably so. Every rank then draws the *same* first
vector, and the first vector is the initial dimer direction, so N independent
searches collapse into one search repeated N times. Measured on
examples/Fe_vacancy at a fixed seed, distinct saddle points found fell from
2 at one rank to 1 at four ranks while the code reported success.

Keying by rank avoids the collapse but leaves results dependent on how many
cores the job used, and on Master_Slave dispatch, which hands tasks out with
MPI.ANY_SOURCE in completion order -- so the stream position at a given draw
varies with machine load. Running one commit twice, hours apart, produced 7
saddle points once and 8 the other time.

Streams are therefore derived from the identity of the *task*, not of the
process: the KMC step, active volume, and search index. A search then draws
the same numbers no matter which rank runs it, how many ranks exist, or in
what order they finish.
"""

import numpy as np

# Stream namespaces. Distinct values keep two consumers that happen to share a
# task identity -- a search direction and an event selection in the same step,
# say -- from drawing the same numbers.
NS_VN = 1           # initial dimer direction for one saddle-point search
NS_KMC_SELECT = 2   # which event fires
NS_KMC_TIME = 3     # residence time in DataKMC
NS_BASIN_TIME = 4   # residence time in Basin

_MASK63 = (1 << 63) - 1


class RandomSource:
    """Reproducible independent streams, addressed by task identity."""

    def __init__(self):
        self._entropy = None

    def seed(self, seed=None):
        """Fix the master seed. ``None`` draws one from OS entropy.

        Returns the seed actually used, so the caller can record it; a run
        that cannot report its own seed is not reproducible even in principle.
        """
        if seed is None:
            seed = int(np.random.SeedSequence().entropy) & _MASK63
        self._entropy = int(seed) & _MASK63
        return self._entropy

    @property
    def master_seed(self):
        if self._entropy is None:
            self.seed(None)
        return self._entropy

    @property
    def is_seeded(self):
        return self._entropy is not None

    def stream(self, *key):
        """A generator for ``key``, a tuple of non-negative integers.

        The same key always yields the same stream within a run, and the same
        stream across runs that share a master seed.
        """
        entropy = [self.master_seed]
        for k in key:
            k = int(k)
            if k < 0:
                raise ValueError(f"stream keys must be non-negative, got {k}")
            entropy.append(k)
        return np.random.default_rng(np.random.SeedSequence(entropy))


random_source = RandomSource()
