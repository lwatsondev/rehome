import inspect

import flask


def log_func(func):
    def wrapper(*args, **kwargs):
        func_args = inspect.signature(func).bind(*args, **kwargs).arguments
        ctx = func_args.get("app", flask)
        ctx.logger.debug(f"{func.__module__}.{func.__qualname__}")
        return func(*args, **kwargs)

    return wrapper
