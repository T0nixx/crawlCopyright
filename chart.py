from matplotlib import pyplot
from matplotlib.axes import Axes

from utils.db_library import get_site_data
from datetime import datetime, timedelta
from pytz import timezone, utc


def convert_iso_to_kst_date(iso_string: str) -> datetime:
    naive_datetime = datetime.fromisoformat(iso_string)
    return utc.localize(naive_datetime).astimezone(timezone("Asia/Seoul")).date()


def main():
    site_data = [
        {
            "main_url": main_url,
            "site_available": site_available,
            # -1 for Z
            "created_date": convert_iso_to_kst_date(created_at[:-1]),
            "last_visited_date": convert_iso_to_kst_date(last_visited_at[:-1]),
        }
        for (
            main_url,
            site_available,
            created_at,
            last_visited_at,
        ) in get_site_data()
    ]

    oldest_created_date: datetime = min(site_data, key=lambda x: x["created_date"])[
        "created_date"
    ]
    latest_visited_date: datetime = site_data[0]["last_visited_date"]

    max_delta: timedelta = latest_visited_date - oldest_created_date
    # available 여부 알기 어려우므로 마지막 날은 일단 제외
    created_available_dict = {
        oldest_created_date + timedelta(days=day): 0 for day in range(max_delta.days)
    }

    for datum in site_data:
        part_delta: timedelta = datum["last_visited_date"] - datum["created_date"]
        for day in range(part_delta.days):
            created_available_dict[datum["created_date"] + timedelta(days=day)] += 1
    x_values = created_available_dict.keys()
    y_values = created_available_dict.values()

    if min(y_values) >= 100:
        ratio = (max(y_values) - min(y_values)) // 50 + 3

        figure, (ax1, ax2) = pyplot.subplots(
            2,
            1,
            sharex=True,
            figsize=(12, 6),
            gridspec_kw={"height_ratios": [ratio, 1]},
        )
        ax1.plot(
            x_values,
            y_values,
            linestyle="-",
            marker="o",
        )

        ax2.plot(
            x_values,
            y_values,
            linestyle="-",
            marker="o",
        )

        ax1.set_ylim(max(0, min(y_values) - 30), max(y_values) + 30)

        figure.text(0.05, 0.5, "Available Sites", va="center", rotation="vertical")
        figure.text(0.5, 0.05, "Date", ha="center", rotation="horizontal")
        # ax1.set_ylabel("Available Sites")
        # ax2.set_xlabel("Date")

        ax2.set_ylim(0, 60)
        ax2.set_yticks([0, 50])

        ax1.spines["bottom"].set_visible(False)
        ax2.spines["top"].set_visible(False)
        ax1.xaxis.tick_top()
        ax1.tick_params(labeltop=False)  # don't put tick labels at the top
        ax2.xaxis.tick_bottom()

        d = 0.015  # how big to make the diagonal lines in axes coordinates
        # arguments to pass to plot, just so we don't keep repeating them
        kwargs = dict(transform=ax1.transAxes, color="k", clip_on=False)
        ax1.plot((-d, +d), (-d, +d), **kwargs)  # top-left diagonal
        ax1.plot((1 - d, 1 + d), (-d, +d), **kwargs)  # top-right diagonal

        kwargs.update(transform=ax2.transAxes)  # switch to the bottom axes
        ax2.plot(
            (-d, +d), (1 - d * ratio, 1 + d * ratio), **kwargs
        )  # bottom-left diagonal
        ax2.plot(
            (1 - d, 1 + d), (1 - d * ratio, 1 + d * ratio), **kwargs
        )  # bottom-right diagonal
    else:
        pyplot.figure(figsize=(12, 9))
        pyplot.plot(
            x_values,
            y_values,
            linestyle="-",
            marker="o",
        )

        pyplot.xlabel("Date")
        pyplot.ylabel("Available sites")
    pyplot.suptitle("Date-Available illegal sites")
    pyplot.show()


if __name__ == "__main__":
    main()