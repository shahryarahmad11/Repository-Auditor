"""Test helpers that let offline tests run without the optional LLM SDK installed."""

import importlib.util
import sys
from types import ModuleType, SimpleNamespace

try:
    HAS_GENAI = importlib.util.find_spec("google.genai") is not None
except (ImportError, ValueError):
    HAS_GENAI = False

if not HAS_GENAI:
    google_module = sys.modules.get("google") or ModuleType("google")
    google_module.__path__ = []
    genai_module = ModuleType("google.genai")
    errors_module = ModuleType("google.genai.errors")
    types_module = ModuleType("google.genai.types")

    class APIError(Exception):
        code = 500

    class SDKObject:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    errors_module.APIError = APIError
    types_module.Type = SimpleNamespace(
        OBJECT="OBJECT", STRING="STRING", INTEGER="INTEGER", ARRAY="ARRAY"
    )
    types_module.Schema = SDKObject
    types_module.FunctionDeclaration = SDKObject
    genai_module.errors = errors_module
    genai_module.types = types_module
    google_module.genai = genai_module
    sys.modules["google"] = google_module
    sys.modules["google.genai"] = genai_module
    sys.modules["google.genai.errors"] = errors_module
    sys.modules["google.genai.types"] = types_module
