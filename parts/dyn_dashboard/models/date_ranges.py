from datetime import datetime, timedelta


def get_selection_date_range(date_filter_selection):
    series = date_filter_selection
    res = eval("get_date_series_" + series.split("_")[0])(  # pylint: disable=W0123
        series.split("_")[1]
    )
    return res


def get_date_series_l(date_filter_selection):  # pragma: no cover
    date_data = {}
    date_filter_options = {
        "day": 0,
        "week": 7,
        "month": 30,
        "quarter": 90,
        "year": 365,
        "past": False,
        "future": False,
    }
    date_data["selected_start_date"] = datetime.strptime(
        (datetime.now() - timedelta(days=date_filter_options[date_filter_selection])).strftime(
            "%Y-%m-%d 00:00:00"
        ),
        "%Y-%m-%d %H:%M:%S",
    )
    date_data["selected_end_date"] = datetime.strptime(
        datetime.now().strftime("%Y-%m-%d 23:59:59"), "%Y-%m-%d %H:%M:%S"
    )
    return date_data


def get_date_series_ls(date_filter_selection):  # pragma: no cover
    return eval("get_date_range_from_" + date_filter_selection)(  # pylint: disable=W0123
        "previous"
    )


def get_date_series_t(date_filter_selection):  # pragma: no cover
    return eval("get_date_range_from_" + date_filter_selection)(  # pylint: disable=W0123
        "current"
    )


def get_date_series_n(date_filter_selection):  # pragma: no cover
    return eval("get_date_range_from_" + date_filter_selection)(  # pylint: disable=W0123
        "next"
    )


def get_date_range_from_day(date_state):
    date_data = {}

    date = datetime.now()

    if date_state == "previous":
        date = date - timedelta(days=1)
    elif date_state == "next":
        date = date + timedelta(days=1)

    date_data["selected_start_date"] = datetime(date.year, date.month, date.day)
    date_data["selected_end_date"] = datetime(date.year, date.month, date.day) + timedelta(
        days=1, seconds=-1
    )
    return date_data


def get_date_range_from_week(date_state):
    date_data = {}

    date = datetime.now()

    if date_state == "previous":
        date = date - timedelta(days=7)
    elif date_state == "next":
        date = date + timedelta(days=7)

    date_iso = date.isocalendar()
    year = date_iso[0]
    week_no = date_iso[1]

    date_data["selected_start_date"] = datetime.strptime(f"{year}-W{week_no}-1", "%G-W%V-%w")
    date_data["selected_end_date"] = date_data["selected_start_date"] + timedelta(
        days=6, hours=23, minutes=59, seconds=59, milliseconds=59
    )
    return date_data


def get_date_range_from_month(date_state):
    date_data = {}

    date = datetime.now()
    year = date.year
    month = date.month

    if date_state == "previous":
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    elif date_state == "next":
        month += 1
        if month == 13:
            month = 1
            year += 1

    end_year = year
    end_month = month
    if month == 12:
        end_year += 1
        end_month = 1
    else:
        end_month += 1

    date_data["selected_start_date"] = datetime(year, month, 1)
    date_data["selected_end_date"] = datetime(end_year, end_month, 1) - timedelta(seconds=1)
    return date_data


def get_date_range_from_quarter(date_state):  # pragma: no cover
    date_data = {}

    date = datetime.now()
    year = date.year
    quarter = int((date.month - 1) / 3) + 1

    if date_state == "previous":
        quarter -= 1
        if quarter == 0:
            quarter = 4
            year -= 1
    elif date_state == "next":
        quarter += 1
        if quarter == 5:
            quarter = 1
            year += 1

    date_data["selected_start_date"] = datetime(year, 3 * quarter - 2, 1)

    month = 3 * quarter
    remaining = int(month / 12)
    date_data["selected_end_date"] = datetime(year + remaining, month % 12 + 1, 1) - timedelta(
        seconds=1
    )

    return date_data


def get_date_range_from_year(date_state):  # pragma: no cover
    date_data = {}

    date = datetime.now()
    year = date.year

    if date_state == "previous":
        year -= 1
    elif date_state == "next":
        year += 1

    date_data["selected_start_date"] = datetime(year, 1, 1)
    date_data["selected_end_date"] = datetime(year + 1, 1, 1) - timedelta(seconds=1)

    return date_data


def get_date_range_from_past(date_state):  # pragma: no cover
    date_data = {}

    date = datetime.now()

    date_data["selected_start_date"] = False
    date_data["selected_end_date"] = date
    return date_data


def get_date_range_from_pastwithout(date_state):  # pragma: no cover
    date_data = {}
    date = datetime.now()
    hour = date.hour + 1
    date = date - timedelta(hours=hour)
    date_data["selected_start_date"] = False
    date_data["selected_end_date"] = date
    return date_data


def get_date_range_from_future(date_state):  # pragma: no cover
    date_data = {}

    date = datetime.now()

    date_data["selected_start_date"] = date
    date_data["selected_end_date"] = False
    return date_data


def get_date_range_from_futurestarting(date_state):  # pragma: no cover
    date_data = {}
    date = datetime.now()
    hour = (24 - date.hour) + 1
    date = date + timedelta(hours=hour)
    date_data["selected_start_date"] = date
    date_data["selected_end_date"] = False
    return date_data
