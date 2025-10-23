import inspect
import re


def trailing_modules(*, module_name: str = "", limit: int = 0, stacklevel: int = 1) -> str:
    """Get the final components of the module name, below any library names, and excluding class/method suffixes.

    :param module_name: The module name to process. Default is the caller's module name.
    :param limit: The maximum number of components in the result. Default is 0 (all).
    :param stacklevel: The stack level to inspect for the module name. Default is 1 (the caller).
    :return str: The final `limit` dot separated components in the module path.
    """
    assert stacklevel > 0, "stacklevel must be greater than 0"
    result: str = module_name or getattr(
        inspect.getmodule(inspect.stack()[stacklevel].frame), "__name__", ""
    )
    result = re.sub(r"\.[_A-Z].*", "", result)  # Exclude private methods and class names
    if limit > 0:
        result = ".".join(result.split(".")[-limit:])
    return result
