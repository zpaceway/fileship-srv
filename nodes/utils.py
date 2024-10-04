import uuid


def generate_random_uuid():
    return uuid.uuid4().hex + uuid.uuid4().hex
