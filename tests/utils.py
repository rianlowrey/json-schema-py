import importlib.util
import sys
from pathlib import Path

def setup():
    moduleRoot = Path(__file__).parent.parent
    moduleSource = moduleRoot.joinpath("json_schema", "__init__.py")

    if moduleRoot not in sys.path:
        sys.path.insert(0, moduleRoot)

    moduleName = Path(moduleSource).parent.name
    spec = importlib.util.spec_from_file_location(moduleName, moduleSource)
    module = importlib.util.module_from_spec(spec)

    sys.modules[moduleName] = module

    spec.loader.exec_module(module)

    return module