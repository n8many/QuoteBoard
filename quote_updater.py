from typing import Optional
import datetime
import gspread
import pandas as pd


# Cleaning functions must be stable (i.e. input = output)

def clean_quotes(df):
    
    # do not modify in place

    # remove ppl manually adding quotation marks to beginning and end of quote
    df = df.fillna('')
    df = df.loc[~(df["Quote"].str.len()==0)]
    df["Quote"] = df["Quote"].str.strip("\"'")
    df = df.set_index(pd.util.hash_pandas_object(df), drop=False)
    return df

def clean_birthdays(df):

    # do not modify in place

    # df = df.reset_index()
    def coerce_birthday(x):
        try:
            if isinstance(x, datetime.date):
                return x
            # Currently does not work for leap day babies, but that's only 1/1461, strips to none
            try:
                return datetime.datetime.strptime(x,'%Y-%m-%d').date()
            except ValueError:
                return datetime.datetime.strptime(x,'%m/%d').date().replace(year=datetime.date.today().year)
        except ValueError:
            return ''
        except TypeError:
            return ''
        
    df['Birthday'] = df['Birthday'].apply(coerce_birthday)
    df = df.fillna('')
    
    return df

def get_spreadsheet(spreadsheet_id: str, sheet_name: str) -> pd.DataFrame():
    # Log in, get workbook, get spreadsheet, save data, return as DataFrame
    gc = gspread.service_account('credentials.json')
    spreadsheet = gc.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(sheet_name)
    # TODO may need some sanitization of stray data
    rows = worksheet.get_all_records()
    data = pd.DataFrame(rows)
    return data

if __name__ == "__main__":
    # We're just gonna leave this out until we rebuild it with JSON
    """
    from config import quote_source, quote_sheet, quote_file, enable_birthday_quotes, birthday_sheet, birthday_file
    quotes = fetch_quotes(quote_source, quote_sheet, quote_file)
    print(quotes)

    if enable_birthday_quotes:
        birthdays = fetch_birthdays(quote_source, birthday_sheet, birthday_file)
        print(birthdays)
    """
    