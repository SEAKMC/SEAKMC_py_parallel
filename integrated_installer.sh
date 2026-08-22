#!/usr/bin/env bash
# =============================================================================
# recreate_seakmc_env.sh
# -----------------------------------------------------------------------------
# Stands up, from a single file, a NON-CONDA Python environment that runs
# SEAKMC_py_parallel (seakmc) with LAMMPS (in-process PyLammps) and OpenKIM
# (kim-api) potentials. Same spirit as recreate_kaltlab_env.sh: self-contained,
# userspace, no root, exact pins where it matters.
#
# Target: the ISAAC cluster (Lmod modules, no sudo, no conda). MPI is taken from
# `module load openmpi/...`; everything else is built or pip-installed into $HOME.
#
# The env has FIVE layers, all reproduced here:
#   1. A relocatable CPython 3.12 (python-build-standalone) under $HOME.
#      3.12 is chosen so SEAKMC's mpi4py<=3.1.6 pin compiles cleanly.
#   2. A pinned PyPI scientific stack (numpy/scipy/pandas/monty/pymatgen/pyyaml).
#   3. mpi4py, compiled against the cluster's OpenMPI *module*.
#   4. kim-api -- the FULL OpenKIM library -- built from source into $HOME.
#      This is only the API/library (~3 MB), NOT the multi-GB 'openkim-models'
#      collection. Individual models are added on demand (see SEAKMC_KIM_MODELS).
#   5. LAMMPS (pinned stable release) built as a SHARED library with the
#      PYTHON + KIM packages, MPI-enabled, installed into the venv as the
#      `lammps` python module. MPI-enabled is REQUIRED: seakmc's PyLammps
#      runner calls lammps(comm=<split mpi4py communicator>), so LAMMPS and
#      mpi4py MUST share the SAME MPI installation.
#
# -----------------------------------------------------------------------------
# QUICK START (on the cluster):
#   module load gcc/13.<x>                       # compiler matching the MPI module
#   SEAKMC_EXTRA_MODULES="gcc/13.<x>" ./recreate_seakmc_env.sh
#
# USE IT (interactive shell or batch script):
#   module load openmpi/4.1.8-gcc13              # the SAME module used to build
#   source ~/.venvs/seakmc/bin/activate          # also pulls in kim-api + libs
#   srun -n <N> python run_seakmc_p.py           # or: seakmc
#
# =============================================================================
# CONFIGURATION -- every dependency has a LOCATION knob and a VERSION knob.
# All are optional; the defaults reproduce the exact validated build.
# Override by exporting the variable, e.g.:
#   SEAKMC_PYMATGEN_VER=2025.6.14 SEAKMC_LAMMPS_TAG=stable_29Aug2024 ./recreate_seakmc_env.sh
#
#   ---- General --------------------------------------------------------------
#   SEAKMC_VENV            venv location            (default ~/.venvs/seakmc)
#   SEAKMC_JOBS            parallel build jobs      (default: nproc, capped 4)
#
#   ---- Python interpreter ---------------------------------------------------
#   SEAKMC_PYTHON          interpreter on PATH to prefer   (default python3.12)
#   SEAKMC_PY_SERIES       CPython minor series to require (default 3.12)
#   SEAKMC_LOCAL_PY        where to install a standalone Python
#                                                   (default ~/.local/python3.12)
#   SEAKMC_FORCE_LOCAL_PY=1  always use the local standalone build
#   SEAKMC_PY_URL          direct python-build-standalone install_only tarball
#                          URL / file path (offline/air-gapped use)
#
#   ---- MPI (LOCATION = a module or an on-PATH mpicc) ------------------------
#   SEAKMC_MPI_MODULE      MPI module to `module load`  (default openmpi/4.1.8-gcc13)
#   SEAKMC_EXTRA_MODULES   extra modules loaded first, space-separated
#                          (e.g. a matching "gcc/13.2.0")
#   (If no `module` system exists, an mpicc/mpicxx already on PATH is used.)
#
#   ---- PyPI scientific stack (VERSIONS) -------------------------------------
#   SEAKMC_NUMPY_VER       (default 2.5.1)      SEAKMC_SCIPY_VER   (default 1.18.0)
#   SEAKMC_PANDAS_VER      (default 3.0.5)      SEAKMC_MONTY_VER   (default 2026.7.16)
#   SEAKMC_PYMATGEN_VER    (default 2026.5.4)   SEAKMC_PYYAML_VER  (default 6.0.3)
#   SEAKMC_MPI4PY_VER      (default 3.1.6; seakmc requires <=3.1.6)
#   SEAKMC_REQ_FILE        path to a requirements.txt to use INSTEAD of the
#                          version knobs above (full control of the pin set)
#
#   ---- kim-api (LOCATION + VERSION) -----------------------------------------
#   SEAKMC_KIM_SRC         source tree           (default ~/kim-api; cloned if absent)
#   SEAKMC_KIM_GIT         git URL               (default openkim/kim-api)
#   SEAKMC_KIM_TAG         git tag/branch/VERSION (default v2.4.2)
#   SEAKMC_KIM_PREFIX      install prefix        (default ~/.local/kim-api)
#   SEAKMC_KIM_MODELS      space-separated OpenKIM model IDs to install after the
#                          build, e.g. "SW_StillingerWeber_1985_Si__MO_405512056662_006"
#                          (default: none -- keeps the install lightweight)
#   SEAKMC_SKIP_KIM=1      don't build; just use an existing kim-api at SEAKMC_KIM_PREFIX
#
#   ---- LAMMPS (LOCATION + VERSION) ------------------------------------------
#   SEAKMC_LAMMPS_SRC      source tree           (default ~/lammps-<tag>)
#   SEAKMC_LAMMPS_GIT      git URL (if set, clone instead of tarball download)
#   SEAKMC_LAMMPS_TAG      release tag/VERSION   (default stable_22Jul2025_update4)
#   SEAKMC_LAMMPS_PKGS     packages to enable    (default: KIM PYTHON MANYBODY
#                          MOLECULE KSPACE EXTRA-PAIR EXTRA-COMPUTE EXTRA-FIX
#                          EXTRA-DUMP RIGID MISC MEAM)
#   SEAKMC_LAMMPS_CMAKE_EXTRA  extra `-D...` cmake flags, space-separated
#   SEAKMC_SKIP_LAMMPS=1   don't build LAMMPS (also auto-skipped if no MPI found)
#
#   ---- seakmc (LOCATION + VERSION) ----------------------------------------
#   SEAKMC_SRC             source tree           (default ~/SEAKMC_py_parallel)
#   SEAKMC_GIT             git URL               (default SEAKMC/SEAKMC_py_parallel)
#   SEAKMC_TAG             git tag/branch/VERSION(default main)
#   SEAKMC_EDITABLE=0      install non-editable (default is editable, -e)
#
#   ---- phonoLAMMPS (phonons for HTST/Arrhenius prefactors) -------------------
#   SEAKMC_PHONOLAMMPS=0      skip it (default: install)
#   SEAKMC_PHONOLAMMPS_VER   phonoLAMMPS version   (default 0.10.1)
#   SEAKMC_PHONOPY_VER       phonopy version       (default 4.4.0)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration + validated defaults
# ---------------------------------------------------------------------------
VENV_DIR="${SEAKMC_VENV:-$HOME/.venvs/seakmc}"
NPROC="$(command -v nproc >/dev/null 2>&1 && nproc || echo 2)"
JOBS="${SEAKMC_JOBS:-$(( NPROC > 4 ? 4 : NPROC ))}"

# Python
PYTHON="${SEAKMC_PYTHON:-python3.12}"
PBS_SERIES="${SEAKMC_PY_SERIES:-3.12}"
LOCAL_PY_PREFIX="${SEAKMC_LOCAL_PY:-$HOME/.local/python${PBS_SERIES}}"
LOCAL_PY_BIN="$LOCAL_PY_PREFIX/bin/python${PBS_SERIES}"
FORCE_LOCAL_PY="${SEAKMC_FORCE_LOCAL_PY:-0}"
PBS_REPO="astral-sh/python-build-standalone"

# MPI
MPI_MODULE="${SEAKMC_MPI_MODULE:-openmpi/4.1.8-gcc13}"
EXTRA_MODULES="${SEAKMC_EXTRA_MODULES:-}"

# PyPI versions (the validated pin set)
NUMPY_VER="${SEAKMC_NUMPY_VER:-2.5.1}"
SCIPY_VER="${SEAKMC_SCIPY_VER:-1.18.0}"
PANDAS_VER="${SEAKMC_PANDAS_VER:-3.0.5}"
MONTY_VER="${SEAKMC_MONTY_VER:-2026.7.16}"
PYMATGEN_VER="${SEAKMC_PYMATGEN_VER:-2026.5.4}"
PYYAML_VER="${SEAKMC_PYYAML_VER:-6.0.3}"
MPI4PY_VER="${SEAKMC_MPI4PY_VER:-3.1.6}"
REQ_FILE="${SEAKMC_REQ_FILE:-}"

# kim-api
KIM_SRC="${SEAKMC_KIM_SRC:-$HOME/kim-api}"
KIM_GIT="${SEAKMC_KIM_GIT:-https://github.com/openkim/kim-api.git}"
KIM_TAG="${SEAKMC_KIM_TAG:-v2.4.2}"
KIM_PREFIX="${SEAKMC_KIM_PREFIX:-$HOME/.local/kim-api}"
KIM_MODELS="${SEAKMC_KIM_MODELS:-}"
SKIP_KIM="${SEAKMC_SKIP_KIM:-0}"

# LAMMPS
LAMMPS_TAG="${SEAKMC_LAMMPS_TAG:-stable_22Jul2025_update4}"
LAMMPS_SRC="${SEAKMC_LAMMPS_SRC:-$HOME/lammps-$LAMMPS_TAG}"
LAMMPS_GIT="${SEAKMC_LAMMPS_GIT:-}"
LAMMPS_PKGS="${SEAKMC_LAMMPS_PKGS:-KIM PYTHON MANYBODY MOLECULE KSPACE EXTRA-PAIR EXTRA-COMPUTE EXTRA-FIX EXTRA-DUMP RIGID MISC MEAM}"
LAMMPS_CMAKE_EXTRA="${SEAKMC_LAMMPS_CMAKE_EXTRA:-}"
SKIP_LAMMPS="${SEAKMC_SKIP_LAMMPS:-0}"

# seakmc
SEAKMC_SRC="${SEAKMC_SRC:-$HOME/SEAKMC_py_parallel}"
SEAKMC_GIT="${SEAKMC_GIT:-https://github.com/SEAKMC/SEAKMC_py_parallel.git}"
SEAKMC_TAG="${SEAKMC_TAG:-main}"
SEAKMC_EDITABLE="${SEAKMC_EDITABLE:-1}"

# phonoLAMMPS: phonons via LAMMPS + phonopy, for HTST/Arrhenius prefactors.
# It's a pure-Python front-end (NOT a LAMMPS compile-time package); it drives the
# LAMMPS python API we build, so it needs no lammps wheel. Installed by default.
INSTALL_PHONOLAMMPS="${SEAKMC_PHONOLAMMPS:-1}"
PHONOLAMMPS_VER="${SEAKMC_PHONOLAMMPS_VER:-0.10.1}"
PHONOPY_VER="${SEAKMC_PHONOPY_VER:-4.4.0}"

LOCK_FILE="$(mktemp /tmp/seakmc_lock.XXXXXX.txt)"
trap 'rm -f "$LOCK_FILE"' EXIT

echo "============================================================"
echo " Recreating the SEAKMC + LAMMPS + OpenKIM environment"
echo "   venv        : $VENV_DIR"
echo "   python      : $PYTHON  (series $PBS_SERIES)"
echo "   MPI module  : $MPI_MODULE ${EXTRA_MODULES:+(+ $EXTRA_MODULES)}"
echo "   kim-api     : $KIM_TAG -> $KIM_PREFIX  (src $KIM_SRC)"
echo "   LAMMPS      : $LAMMPS_TAG  [$LAMMPS_PKGS]"
echo "   seakmc    : $SEAKMC_TAG  (src $SEAKMC_SRC)"
echo "   phonoLAMMPS : $([ "$INSTALL_PHONOLAMMPS" = 1 ] && echo "$PHONOLAMMPS_VER (+ phonopy $PHONOPY_VER)" || echo disabled)"
echo "   build jobs  : $JOBS"
echo "============================================================"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
py_series_version() {   # echo "X.Y.Z" and return 0 iff $1 is a usable Python $PBS_SERIES.*
    command -v "$1" >/dev/null 2>&1 || return 1
    local v
    v="$("$1" -c 'import sys;print("%d.%d.%d"%sys.version_info[:3])' 2>/dev/null)" || return 1
    case "$v" in ${PBS_SERIES}.*) printf '%s' "$v"; return 0 ;; *) return 1 ;; esac
}

# Return 0 iff interpreter $1 ships development headers (Python.h). Required to
# compile mpi4py and the LAMMPS python bindings against it; many cluster system
# pythons omit the -devel headers, which breaks those builds.
py_has_headers() {
    "$1" - <<'PY' >/dev/null 2>&1
import os, sysconfig
inc = sysconfig.get_path('include')
raise SystemExit(0 if inc and os.path.exists(os.path.join(inc, 'Python.h')) else 1)
PY
}

# fetch_repo <srcdir> <giturl> <tag> <sentinel-file>
# Respects an existing tree (does not touch a user-provided location); otherwise
# clones at the requested tag/branch.
fetch_repo() {
    local src="$1" url="$2" tag="$3" sentinel="$4"
    if [ -e "$src/$sentinel" ]; then
        echo "  using existing source at $src (not modified)"
        return 0
    fi
    echo "  cloning $url${tag:+ @ $tag} -> $src"
    if [ -n "$tag" ]; then
        git clone --depth 1 --branch "$tag" "$url" "$src"
    else
        git clone --depth 1 "$url" "$src"
    fi
}

provision_local_python() {
    local arch triple url tmp dl api
    arch="$(uname -m)"
    case "$arch" in
        x86_64)  triple="x86_64-unknown-linux-gnu" ;;
        aarch64) triple="aarch64-unknown-linux-gnu" ;;
        *) echo "  ERROR: no prebuilt Python for arch '$arch'; set SEAKMC_PY_URL." ; exit 1 ;;
    esac
    if   command -v curl >/dev/null 2>&1; then dl="curl"
    elif command -v wget >/dev/null 2>&1; then dl="wget"
    else echo "  ERROR: need curl or wget to download Python." ; exit 1 ; fi

    url="${SEAKMC_PY_URL:-}"
    if [ -z "$url" ]; then
        echo "    locating a CPython ${PBS_SERIES} ($triple) install_only build in latest ${PBS_REPO} release..."
        if [ "$dl" = "curl" ]; then
            api="$(curl -fsSL "https://api.github.com/repos/${PBS_REPO}/releases/latest" 2>/dev/null || true)"
        else
            api="$(wget -qO- "https://api.github.com/repos/${PBS_REPO}/releases/latest" 2>/dev/null || true)"
        fi
        url="$(printf '%s' "$api" \
            | grep -oE "https://[^\"]*cpython-${PBS_SERIES}\.[0-9]+(\+|%2B)[0-9]+-${triple}-install_only\.tar\.gz" \
            | head -1 || true)"
    fi
    if [ -z "$url" ]; then
        echo "  ERROR: could not determine a Python download URL (no network, or no"
        echo "         matching build). Pre-download a python-build-standalone"
        echo "         'install_only' tarball for $triple and re-run with:"
        echo "             SEAKMC_PY_URL=/path/to/cpython-...-install_only.tar.gz $0"
        exit 1
    fi
    echo "    fetching: $url"
    tmp="$(mktemp -d)"
    local localfile="$url"
    [ "${localfile#file://}" != "$localfile" ] && localfile="${localfile#file://}"
    if [ -f "$localfile" ]; then cp "$localfile" "$tmp/py.tgz"
    elif [ "$dl" = "curl" ]; then curl -fSL "$url" -o "$tmp/py.tgz"
    else wget -q "$url" -O "$tmp/py.tgz"; fi
    echo "    extracting into $LOCAL_PY_PREFIX"
    rm -rf "$LOCAL_PY_PREFIX"; mkdir -p "$LOCAL_PY_PREFIX"
    tar -xzf "$tmp/py.tgz" -C "$tmp"
    cp -a "$tmp/python/." "$LOCAL_PY_PREFIX/"
    rm -rf "$tmp"
    [ -e "$LOCAL_PY_BIN" ] || ln -sf python3 "$LOCAL_PY_BIN"
}

# ---------------------------------------------------------------------------
# 1. Resolve the MPI toolchain (module load on the cluster)
# ---------------------------------------------------------------------------
echo ""
echo "[1/7] Resolving MPI..."
HAVE_MPI=0
if command -v module >/dev/null 2>&1 || [ -n "${MODULESHOME:-}" ]; then
    for m in $EXTRA_MODULES; do
        echo "  module load $m"
        module load "$m" 2>/dev/null || echo "    (warning: could not load $m)"
    done
    echo "  module load $MPI_MODULE"
    module load "$MPI_MODULE" 2>/dev/null || {
        echo "  WARNING: 'module load $MPI_MODULE' failed. Set SEAKMC_MPI_MODULE to an"
        echo "           available module (see: module avail openmpi)."
    }
fi
if command -v mpicc >/dev/null 2>&1 && command -v mpicxx >/dev/null 2>&1; then
    HAVE_MPI=1
    echo "  mpicc : $(command -v mpicc)"
    echo "  mpicxx: $(command -v mpicxx)"
    mpicc --showme:version 2>/dev/null | head -1 || mpicc --version 2>/dev/null | head -1 || true
else
    echo "  No MPI compilers (mpicc/mpicxx) on PATH -> mpi4py and LAMMPS will be SKIPPED."
    echo "  On the cluster set SEAKMC_MPI_MODULE (+ SEAKMC_EXTRA_MODULES for gcc)."
fi

# ---------------------------------------------------------------------------
# 2. Resolve / provision a Python interpreter
# ---------------------------------------------------------------------------
echo ""
echo "[2/7] Resolving a Python $PBS_SERIES interpreter (with dev headers)..."
PYVER=""; PICK=""
# Prefer an on-PATH interpreter, but ONLY if it has Python.h (needed to build
# mpi4py + LAMMPS bindings). A headerless system python is rejected in favour of
# the standalone build, which bundles its headers.
if [ "$FORCE_LOCAL_PY" != "1" ] && PYVER="$(py_series_version "$PYTHON")"; then
    if py_has_headers "$PYTHON"; then
        PICK="$PYTHON"; echo "  Using on-PATH $PYTHON (Python $PYVER, headers present)."
    else
        echo "  On-PATH $PYTHON (Python $PYVER) has NO dev headers (Python.h) -- can't"
        echo "  build mpi4py/LAMMPS against it; falling back to a standalone build."
    fi
fi
if [ -z "$PICK" ] && PYVER="$(py_series_version "$LOCAL_PY_BIN")" && py_has_headers "$LOCAL_PY_BIN"; then
    PICK="$LOCAL_PY_BIN"; echo "  Using local interpreter $LOCAL_PY_BIN (Python $PYVER)."
fi
if [ -z "$PICK" ]; then
    echo "  Installing a local standalone Python $PBS_SERIES under \$HOME (bundles headers)..."
    provision_local_python
    PICK="$LOCAL_PY_BIN"
    PYVER="$(py_series_version "$PICK")" || { echo "  ERROR: local Python provisioning failed."; exit 1; }
    py_has_headers "$PICK" || { echo "  ERROR: standalone Python is missing headers?!"; exit 1; }
    echo "  Installed local interpreter: $PICK (Python $PYVER)"
fi
PYTHON="$PICK"

# ---------------------------------------------------------------------------
# 3. Create the venv + pinned scientific stack
# ---------------------------------------------------------------------------
echo ""
echo "[3/7] Creating venv and installing the pinned PyPI stack..."
[ -d "$VENV_DIR" ] && { echo "  Existing venv found -- removing."; rm -rf "$VENV_DIR"; }
mkdir -p "$(dirname "$VENV_DIR")"
"$PYTHON" -m venv "$VENV_DIR"
VPY="$VENV_DIR/bin/python"
$VPY -m pip install --upgrade pip setuptools wheel
$VPY -m pip install cmake ninja           # userspace build tools; no root needed
if [ -n "$REQ_FILE" ]; then
    echo "  using requirements file: $REQ_FILE"
    cp "$REQ_FILE" "$LOCK_FILE"
else
    cat > "$LOCK_FILE" <<EOF
numpy==$NUMPY_VER
scipy==$SCIPY_VER
pandas==$PANDAS_VER
monty==$MONTY_VER
pymatgen==$PYMATGEN_VER
PyYAML==$PYYAML_VER
EOF
fi
$VPY -m pip install -r "$LOCK_FILE"
export PATH="$VENV_DIR/bin:$PATH"          # cmake/ninja from the venv

# ---------------------------------------------------------------------------
# 4. mpi4py, compiled against the loaded MPI
# ---------------------------------------------------------------------------
echo ""
echo "[4/7] Installing mpi4py==$MPI4PY_VER (compiled against MPI)..."
if [ "$HAVE_MPI" = "1" ]; then
    # mpi4py 3.1.x's bundled mpidistutils calls new_compiler(dry_run=..., force=...),
    # parameters that setuptools>=72 REMOVED. pip's isolated build env pulls the
    # latest setuptools (and ignores PIP_CONSTRAINT for build deps), so the wheel
    # build fails with:
    #   TypeError: new_compiler() got an unexpected keyword argument 'dry_run'
    # Deterministic fix: DISABLE build isolation and provide the pinned build
    # backend (setuptools<72 + wheel) in the venv itself, then build mpi4py
    # against it. Restore a modern setuptools afterwards.
    SETUPTOOLS_SAVED="$($VPY -c 'import setuptools;print(setuptools.__version__)' 2>/dev/null || echo '')"
    $VPY -m pip install "setuptools<72" wheel
    MPICC="$(command -v mpicc)" $VPY -m pip install --no-build-isolation --no-binary=mpi4py "mpi4py==$MPI4PY_VER"
    if [ -n "$SETUPTOOLS_SAVED" ]; then
        $VPY -m pip install --upgrade "setuptools==$SETUPTOOLS_SAVED" || $VPY -m pip install --upgrade setuptools
    fi
else
    echo "  SKIPPED (no MPI). seakmc cannot be imported without mpi4py."
fi

# ---------------------------------------------------------------------------
# 5. kim-api (full OpenKIM library) from source
# ---------------------------------------------------------------------------
echo ""
echo "[5/7] kim-api (full library) -> $KIM_PREFIX ..."
if [ "$SKIP_KIM" = "1" ]; then
    echo "  SKIPPED build (SEAKMC_SKIP_KIM=1); using existing $KIM_PREFIX."
else
    fetch_repo "$KIM_SRC" "$KIM_GIT" "$KIM_TAG" "CMakeLists.txt"
    (
        cd "$KIM_SRC"
        rm -rf build && mkdir build && cd build
        cmake .. -DCMAKE_INSTALL_PREFIX="$KIM_PREFIX" \
                 -DCMAKE_BUILD_TYPE=Release \
                 -DKIM_API_BUILD_EXAMPLES=OFF
        make -j"$JOBS"
        make install
    )
fi
# Activate kim-api so libkim-api.so is discoverable to the LAMMPS build + runtime.
# kim-api-activate references $ZSH_VERSION/$BASH_VERSION unguarded -> relax `set -u`.
if [ -f "$KIM_PREFIX/bin/kim-api-activate" ]; then
    set +u
    # shellcheck disable=SC1090
    source "$KIM_PREFIX/bin/kim-api-activate"
    set -u
fi
export CMAKE_PREFIX_PATH="$KIM_PREFIX:${CMAKE_PREFIX_PATH:-}"
export PKG_CONFIG_PATH="$KIM_PREFIX/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
export LD_LIBRARY_PATH="$KIM_PREFIX/lib:${LD_LIBRARY_PATH:-}"
echo "  kim-api $(kim-api-collections-management list 2>/dev/null | awk '/kim-api /{print $2; exit}') ready."
# Optional: install specific interatomic models (keeps default install lightweight)
if [ -n "$KIM_MODELS" ]; then
    for mdl in $KIM_MODELS; do
        echo "  installing OpenKIM model: $mdl"
        kim-api-collections-management install user "$mdl" || echo "    (warning: failed to install $mdl)"
    done
else
    echo "  (no models installed -- add later: kim-api-collections-management install user <ModelName>)"
fi

# ---------------------------------------------------------------------------
# 6. LAMMPS: shared lib + PYTHON + KIM, MPI-enabled, installed into the venv
# ---------------------------------------------------------------------------
echo ""
echo "[6/7] Building LAMMPS ($LAMMPS_TAG) as the venv 'lammps' module..."
if [ "$SKIP_LAMMPS" = "1" ]; then
    echo "  SKIPPED (SEAKMC_SKIP_LAMMPS=1)."
elif [ "$HAVE_MPI" != "1" ]; then
    echo "  SKIPPED (no MPI). LAMMPS must be MPI-enabled to match mpi4py; build it"
    echo "  where an OpenMPI module/compilers are available (i.e. on the cluster)."
else
    if [ -f "$LAMMPS_SRC/cmake/CMakeLists.txt" ]; then
        echo "  using existing LAMMPS source at $LAMMPS_SRC"
    elif [ -n "$LAMMPS_GIT" ]; then
        fetch_repo "$LAMMPS_SRC" "$LAMMPS_GIT" "$LAMMPS_TAG" "cmake/CMakeLists.txt"
    else
        echo "  fetching LAMMPS $LAMMPS_TAG (tarball)..."
        tmp="$(mktemp -d)"
        url="https://github.com/lammps/lammps/archive/refs/tags/${LAMMPS_TAG}.tar.gz"
        if command -v curl >/dev/null 2>&1; then curl -fSL "$url" -o "$tmp/lmp.tgz"
        else wget -q "$url" -O "$tmp/lmp.tgz"; fi
        mkdir -p "$LAMMPS_SRC"
        tar -xzf "$tmp/lmp.tgz" -C "$LAMMPS_SRC" --strip-components=1
        rm -rf "$tmp"
    fi
    PKG_FLAGS=()
    for p in $LAMMPS_PKGS; do PKG_FLAGS+=("-DPKG_${p}=on"); done
    (
        cd "$LAMMPS_SRC"
        rm -rf build && mkdir build && cd build
        # shellcheck disable=SC2086
        cmake ../cmake \
            -G Ninja \
            -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_INSTALL_PREFIX="$VENV_DIR" \
            -DBUILD_MPI=yes \
            -DBUILD_SHARED_LIBS=yes \
            -DLAMMPS_EXCEPTIONS=yes \
            -DPKG_KIM=yes -DDOWNLOAD_KIM=no \
            -DPython_EXECUTABLE="$VPY" \
            "${PKG_FLAGS[@]}" $LAMMPS_CMAKE_EXTRA
        cmake --build . -j "$JOBS"
        # Installs the `lammps` python package AND liblammps.so into the venv
        # (CMAKE_INSTALL_PREFIX is the venv); no LD_LIBRARY_PATH needed for it.
        cmake --build . --target install-python
    )
    echo "  LAMMPS python module installed into the venv."
fi

# ---------------------------------------------------------------------------
# 7. phonoLAMMPS + seakmc + activation wiring + verification
# ---------------------------------------------------------------------------
echo ""
echo "[7/7] Installing phonoLAMMPS + seakmc and verifying..."

# --- phonoLAMMPS (phonons -> HTST/Arrhenius prefactors, via LAMMPS + phonopy) ---
if [ "$INSTALL_PHONOLAMMPS" = "1" ]; then
    echo "  phonoLAMMPS==$PHONOLAMMPS_VER (+ phonopy==$PHONOPY_VER)"
    # Constrain to the core pins ($LOCK_FILE) so numpy/scipy/pandas/pymatgen stay
    # put. phonoLAMMPS itself is pure-python and pulls NO lammps wheel (it uses the
    # source-built LAMMPS python module at runtime).
    $VPY -m pip install -c "$LOCK_FILE" "phonoLAMMPS==$PHONOLAMMPS_VER" "phonopy==$PHONOPY_VER"
else
    echo "  phonoLAMMPS: SKIPPED (SEAKMC_PHONOLAMMPS=0)."
fi

# --- seakmc ---
fetch_repo "$SEAKMC_SRC" "$SEAKMC_GIT" "$SEAKMC_TAG" "setup.py"
# --no-deps: mpi4py + lammps are provided above; the rest are pinned in the venv.
if [ "$SEAKMC_EDITABLE" = "1" ]; then
    $VPY -m pip install --no-deps -e "$SEAKMC_SRC"
else
    $VPY -m pip install --no-deps "$SEAKMC_SRC"
fi

# Wire kim-api + lib paths into the venv activate so `source activate` is enough
# at runtime. (You STILL must `module load $MPI_MODULE` in your job for the MPI
# runtime that mpi4py and liblammps.so were linked against.)
ACT="$VENV_DIR/bin/activate"
if ! grep -q "seakmc env wiring" "$ACT" 2>/dev/null; then
    {
        echo ""
        echo "# --- seakmc env wiring (added by recreate_seakmc_env.sh) ---"
        echo "# (kim-api-activate uses unguarded \$ZSH_VERSION; relax nounset around it)"
        echo "if [ -f \"$KIM_PREFIX/bin/kim-api-activate\" ]; then"
        echo "    case \$- in *u*) _seakmc_u=1; set +u;; *) _seakmc_u=0;; esac"
        echo "    source \"$KIM_PREFIX/bin/kim-api-activate\""
        echo "    [ \"\$_seakmc_u\" = 1 ] && set -u; unset _seakmc_u"
        echo "fi"
        echo "export LD_LIBRARY_PATH=\"$KIM_PREFIX/lib:\${LD_LIBRARY_PATH:-}\""
        echo "# Reminder: 'module load $MPI_MODULE' is still required for MPI at runtime."
    } >> "$ACT"
fi

echo ""
echo "  Verifying imports..."
"$VPY" - <<'PYEOF'
import importlib, sys
core = ["numpy","scipy","pandas","monty","pymatgen","yaml"]
bad = []
def check(mods, optional=False):
    for m in mods:
        try:
            mod = importlib.import_module(m)
            print(f"  OK  {m:12s} {getattr(mod,'__version__','ok')}")
        except Exception as e:
            print(f"  {'--' if optional else 'XX'}  {m:12s} {e}")
            if not optional: bad.append(m)
check(core)
check(["phonopy", "phonolammps"], optional=True)   # phonons for HTST prefactors
check(["mpi4py"], optional=True)
check(["lammps"], optional=True)
try:
    import mpi4py  # noqa
    check(["seakmc"])
except Exception:
    print("  --  seakmc      (skipped: needs mpi4py/MPI runtime)")
if bad:
    print(f"\n  {len(bad)} core package(s) failed: {', '.join(bad)}"); sys.exit(1)
print("\n  Core environment imports cleanly.")
PYEOF

echo ""
echo "============================================================"
echo " Done. venv: $VENV_DIR   (Python $PYVER)"
echo ""
echo " To use it (interactive shell or batch script):"
echo "     module load $MPI_MODULE"
for m in $EXTRA_MODULES; do echo "     module load $m"; done
echo "     source $VENV_DIR/bin/activate"
echo "     srun -n <N> python run_seakmc_p.py     # or: seakmc"
echo ""
echo " OpenKIM: enable per-run in the seakmc input YAML (potential.OpenKIM),"
echo " and install the model first, e.g.:"
echo "     kim-api-collections-management install user <ModelName>"
if [ "$INSTALL_PHONOLAMMPS" = "1" ]; then
    echo ""
    echo " phonoLAMMPS (phonons -> HTST/Arrhenius prefactors) is installed:"
    echo "     from phonolammps import Phonolammps    # drives the LAMMPS python API"
fi
echo "============================================================"
