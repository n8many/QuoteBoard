import random
from datetime import date, datetime
import pandas as pd

from typing import Optional

def date_is_today(x):
        today = date.today()
        try:
            return x.month==today.month and x.day==today.day
        except ValueError:
            return False
        except AttributeError:
            return False


def pick_random_index(quotes: pd.DataFrame):
    if len(quotes) == 0:
        return None
    else:
        return quotes.index[random.randint(0, len(quotes)-1)]


def filter_recent_quotes(quotes: pd.DataFrame, recent_quotes: pd.Series):
    # Remove from list any quotes that have been used recently (defined by anti-repeat depth)
    return quotes.loc[~quotes.index.isin(recent_quotes)]


def filter_quotes_by_name(quotes, names):
    return quotes.loc[quotes['Who'].isin(names)]


def filter_quotes_by_date(quotes, target_date):
    def coerce_dates(x):
        try:
            return date.fromisoformat(x)
        except ValueError:
            return None
    
    date_quotes = quotes.loc[~quotes['Date'].apply(coerce_dates).isna()].copy()
    
    return date_quotes.loc[date_quotes['Date'].apply(coerce_dates).apply(date_is_today)]


def pick_quote(quotes: pd.DataFrame, recent_quotes: Optional[list] = None, birthdays: Optional[pd.DataFrame] = None, enable_quoteversary: bool = False):
    # Pick a quote from the list, with options for birthdays and quote anniversaries
    new_quotes = filter_recent_quotes(quotes, recent_quotes)

    if birthdays is not None and (bday_index:=pick_birthday_quote(new_quotes, birthdays)) is not None:
        return bday_index
    
    if enable_quoteversary and (qv_index:=pick_quoteversary_quote(new_quotes)) is not None:
        return qv_index
        
    if index := pick_random_index(new_quotes):
        return index
    else:
        # No unused quotes, ignore the recent list
        return pick_random_index(quotes)

def get_current_birthdays(birthdays):
    return birthdays.loc[birthdays['Birthday'].apply(date_is_today)]


def pick_birthday_quote(quotes, birthdays):
    # Pick a quote from the birthday person
    current_birthdays=get_current_birthdays(birthdays)

    if current_birthdays.empty:
        return None
    else:
        return pick_random_index(filter_quotes_by_name(quotes, current_birthdays['Name'].tolist()))
    

def pick_quoteversary_quote(quotes):
    # Pick a quote that happened on today's date, respects repeats
    today_quotes = filter_quotes_by_date(quotes, date.today())

    if today_quotes.empty:
        return None
    else:
        return pick_random_index(today_quotes)