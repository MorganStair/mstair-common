# File: python/plib_/base/caller_module_name_and_level.py

import inspect
from types import FrameType


__all__ = [
    "caller_module_name_and_level",
]


def caller_module_name_and_level(
    *, stacklevel: int = 1, skip_module_frames: bool = True
) -> tuple[str, int]:
    """
    Resolve the name of the calling module and return it along with its actual stacklevel.

    This function traverses the call stack, skipping `<module>` frames if requested,
    and returns the first meaningful module name it finds. It also returns the absolute
    stack level at which that module was located - useful for logging frameworks that
    require accurate stacklevel adjustment.

    :param stacklevel: Number of meaningful (non-<module>) frames to skip.
    :param skip_module_frames: Skip top-level frames like `<module>`. Default is True.
    :return tuple[str, int]: (module name or "", number of frames walked from this call)
    """
    if stacklevel < 1:
        raise ValueError("stacklevel must be greater than 0")

    frame: FrameType | None = inspect.currentframe()
    resolved_level = 0
    resolved_name = ""
    try:
        for _ in range(stacklevel):
            # Skip "<module>" frames if requested
            while skip_module_frames and frame and frame.f_code.co_name == "<module>":
                frame = frame.f_back
                resolved_level += 1

            if not frame:
                break

            frame = frame.f_back
            resolved_level += 1

        if frame:
            module = inspect.getmodule(frame)
            if module and module.__name__:
                resolved_name = module.__name__

        return resolved_name, resolved_level

    finally:
        # Break reference cycle: frame -> f_locals -> frame; helps cyclic GC reclaim memory promptly
        del frame


# End of file: python/plib_/base/caller_module_name_and_level.py
