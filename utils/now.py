import datetime


def now():
    return (
        datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")[:-6]
        + "Z"
    )
