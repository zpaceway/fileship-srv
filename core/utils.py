import time


def auto_retry(func):

    def wrapped(*args, __retry=0, __delay=1, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            if __retry >= 10:
                raise e

            func_arguments = {"args": args, "kwargs": kwargs}

            print(
                f"Failed to execute {func} with {func_arguments}, exception {e} was raised. Retrying after 1 second"
            )
            time.sleep(__delay)
            return wrapped(*args, __retry=__retry + 1, __delay=__delay, **kwargs)

    return wrapped
