import sys, importlib, pkg_resources
from os.path import basename

# All this does is "from * import *", if python only accepted that
# https://stackoverflow.com/questions/43059267/how-to-do-from-module-import-using-importlib
for module in pkg_resources.resource_listdir("oskb.im", ""):
    if module.startswith("_"):
        continue
    module = basename(module)[:-3]
    modhandle = importlib.import_module("oskb.im." + module)
    names = [x for x in modhandle.__dict__ if not x.startswith("_")]
    globals().update({k: getattr(modhandle, k) for k in names})


# Return a default handler for a given platform


def default():
    if sys.platform.startswith("linux"):
        return UInput()
