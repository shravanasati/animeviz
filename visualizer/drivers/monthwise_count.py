from io import BytesIO
from datetime import date

import pendulum
from matplotlib import pyplot as plt

from .base import IVisualizationDriver, VisualizationResult


class _MonthYear:
    def __init__(self, date_: date) -> None:
        self.month_name = date_.strftime("%b")
        self.month = date_.month
        self.year = date_.year
        self.days_in_month = pendulum.parse(str(date_)).days_in_month

    @classmethod
    def fromisoformat(cls, s: str):
        date_ = date.fromisoformat(s)
        return cls(date_)

    def __repr__(self) -> str:
        return f"{self.month_name} {self.year}"

    def __eq__(self, other):
        if isinstance(other, _MonthYear):
            return self.month == other.month and self.year == other.year
        return False

    def __hash__(self):
        return hash((self.month, self.year))

    def __lt__(self, other) -> bool:
        if isinstance(other, _MonthYear):
            if self.year != other.year:
                return self.year < other.year
            elif self.month != other.month:
                return self.month < other.month
            else:
                return False

        return NotImplemented


class MonthwiseCountDriver(IVisualizationDriver):
    def visualize(self) -> VisualizationResult:
        # flag to skip adjusting data for multiple months discrepancy
        # todo what about these flags
        SKIP_ADJUST = False
        AVERAGE = True

        # get a set of unique month-year combinations
        month_years = [
            _MonthYear.fromisoformat(i)
            for i in self.df["my_start_date"]
            if i != "0000-00-00"
        ]
        unique_month_years = set(month_years)
        data = {k: 0 for k in sorted(unique_month_years)}

        # todo count only last 12 months
        for _, row in self.df.iterrows():
            if row["my_start_date"] == "0000-00-00":
                continue

            start_date = _MonthYear.fromisoformat(row["my_start_date"])
            end_date = _MonthYear(date.today())

            if SKIP_ADJUST:
                data[start_date] += int(row["my_watched_episodes"])
                continue

            if row["my_finish_date"] != "0000-00-00":
                end_date = _MonthYear.fromisoformat(row["my_finish_date"])

            start_end_same = start_date == end_date

            if start_end_same:
                data[start_date] += int(row["my_watched_episodes"])
            else:
                pd_start_date = pendulum.parse(row["my_start_date"])
                if row["my_finish_date"] != "0000-00-00":
                    pd_end_date = pendulum.parse(row["my_finish_date"])
                else:
                    pd_end_date = pendulum.today()

                days = pd_start_date.diff(pd_end_date).days
                episodes_per_day = row["my_watched_episodes"] / days
                period = pd_end_date.diff(pd_start_date)
                for m in period.range("months"):
                    if m.month == pd_end_date.month:
                        days_in_month = pd_end_date.date().day
                    else:
                        days_in_month = pd_start_date.diff(m.end_of("month")).days
                    # reset start date
                    pd_start_date = m.end_of("month")
                    try:
                        data[_MonthYear(m)] += int(days_in_month * episodes_per_day)
                    except KeyError:
                        data[_MonthYear(m)] = int(days_in_month * episodes_per_day)

        fig, ax = plt.subplots()
        ax.set_title("Number of anime episodes watched per month")
        if AVERAGE:
            ax.set_ylabel("Number of episodes watched (on daily average)")
            for k, v in data.items():
                data[k] = round(v / k.days_in_month, 2)
        else:
            ax.set_ylabel("Number of episodes watched")

        ax.set_xlabel("Months")
        keys = sorted(data.keys())[-12:]
        values = [data[k] for k in keys]
        bar = ax.bar([str(i) for i in keys], values)
        fig.autofmt_xdate()  # rotate the xticks for better readability
        ax.bar_label(bar)
        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)

        result = VisualizationResult(
            "Monthwise Count", self.to_base64(buf).decode("utf-8")
        )

        return result
