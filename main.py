"""
Render deploy entry point for clan-auth-service.
Locates the real service directory regardless of where Render runs this from,
then loads the actual app so `uvicorn main:app` works with no dashboard changes.
"""
import os, sys, importlib.util

_here = os.path.dirname(os.path.abspath(__file__))

# Try both possible layouts (git-root or inner-repo as CWD)
_candidates = [
    os.path.join(_here, "clan-identity-be", "services", "auth-service"),
    os.path.join(_here, "services", "auth-service"),
]
_service_dir = next((d for d in _candidates if os.path.isdir(d)), None)
if not _service_dir:
    raise ImportError(f"Cannot locate auth-service under {_here!r}")

_libs_dir = os.path.abspath(os.path.join(_service_dir, "..", "..", "libs"))

sys.path.insert(0, _libs_dir)
sys.path.insert(0, _service_dir)

_spec = importlib.util.spec_from_file_location(
    "_auth_service_main",
    os.path.join(_service_dir, "main.py"),
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["_auth_service_main"] = _mod
_spec.loader.exec_module(_mod)

app = _mod.app
