"""Backwards-compatibility alias for the renamed ``seakmc`` package.

The package was published as ``seakmc``, renamed to ``seakmc_p``, and has now
been renamed back to ``seakmc``. This shim maps every ``seakmc_p.*`` name onto
the corresponding ``seakmc.*`` module.

It is required, not merely a courtesy. Checkpoints are pickled object graphs,
and pickle records the fully-qualified module path of every class it stores
(``seakmc_p.kmc.KMC.SuperBasin``, and so on). Without this alias:

* restart files written by the ``seakmc_p`` releases would fail to load, losing
  the checkpoints of anyone mid-campaign; and
* the pre-rename restart files under ``examples/``, which record ``seakmc.*``
  paths, would stay unloadable as they have been since the first rename.

Note that restoring the module paths makes those files *unpickle* again; it
does not make every one of them resumable. The example checkpoints predate the
addition of ``SuperBasin.meanpref``, and pickle restores ``__dict__`` without
calling ``__init__`` or ``initialization()``, so attributes added later are
simply absent and a resume fails with ``AttributeError``. That is class-schema
drift rather than a naming problem, and it is an argument for replacing the
pickle checkpoint format with a versioned one.

Two details matter for correctness:

* ``sys.modules[__name__] = seakmc`` alone is not enough, because
  ``pickle.Unpickler.find_class`` imports the full dotted path rather than the
  top-level package, so submodules have to resolve too.
* The finder must supply a loader that returns the *already imported* module.
  Returning the target's own ``__spec__`` makes the import machinery execute
  the module a second time into a distinct object, and pickle then rejects the
  duplicated classes with "it's not the same object as ...".

This shim is deprecated and will be removed in a future release. Update
``import seakmc_p`` to ``import seakmc``.
"""

import importlib
import importlib.abc
import importlib.util
import sys
import warnings

_OLD = "seakmc_p"
_NEW = "seakmc"


class _AliasLoader(importlib.abc.Loader):
    """Bind an alias name to a module that is already imported."""

    def __init__(self, target):
        self._target = target

    def create_module(self, spec):
        return importlib.import_module(self._target)

    def exec_module(self, module):
        # Already executed under its real name; re-running it would produce
        # duplicate class objects and break pickle round-trips.
        pass


class _AliasFinder(importlib.abc.MetaPathFinder):
    """Resolve ``seakmc_p`` and ``seakmc_p.<sub>`` to their ``seakmc`` twins."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname != _OLD and not fullname.startswith(_OLD + "."):
            return None
        new_name = _NEW + fullname[len(_OLD):]
        try:
            module = importlib.import_module(new_name)
        except ImportError:
            return None
        spec = importlib.util.spec_from_loader(fullname, _AliasLoader(new_name))
        # Mirror package-ness so that deeper submodules keep resolving.
        if hasattr(module, "__path__"):
            spec.submodule_search_locations = list(module.__path__)
        return spec


if not any(isinstance(f, _AliasFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _AliasFinder())

warnings.warn(
    "'seakmc_p' has been renamed to 'seakmc'. The old name still works but "
    "will be removed in a future release; please import 'seakmc' instead.",
    DeprecationWarning,
    stacklevel=2,
)

_seakmc = importlib.import_module(_NEW)
__version__ = _seakmc.__version__
__path__ = list(_seakmc.__path__)


def __getattr__(name):
    return getattr(_seakmc, name)
