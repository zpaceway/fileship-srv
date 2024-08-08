import time


def get_response_from_callback_or_retry_on_error(func, retry=0):
    response = func()

    try:
        response.raise_for_status()
        return response
    except Exception as e:
        if retry >= 10:
            raise e

        time.sleep(1)
        return get_response_from_callback_or_retry_on_error(func, retry=retry + 1)
