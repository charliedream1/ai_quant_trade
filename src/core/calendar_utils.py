"""Date validation and optional Chinese workday helpers without import-time side effects."""

from datetime import date, datetime
from importlib import import_module


def validate(date_text):
    datetime.strptime(str(date_text), "%Y-%m-%d")


def split_hour_minutes(check_time):
    parsed = datetime.strptime(check_time, "%H:%M")
    return parsed.hour, parsed.minute


def after_query_time(check_time):
    now = datetime.now()
    return (now.hour, now.minute) >= split_hour_minutes(check_time)


def is_workdays(value):
    return import_module("chinese_calendar").is_workday(date(value.year, value.month, value.day))


def is_holidays(value):
    return import_module("chinese_calendar").is_holiday(date(value.year, value.month, value.day))


def is_festival(value):
    return import_module("chinese_calendar").get_holiday_detail(date(value.year, value.month, value.day))
