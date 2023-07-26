from typing import Optional

import gspread
import pandas as pd

def clean_quotes(df):
    
    # do not modify in place

    # remove ppl manually adding quotation marks to beginning and end of quote
    # df["Quote"] = df["Quote"].str.strip("\"'")
    df = df.set_index(pd.util.hash_pandas_object(df), drop=False)
    df = df.fillna('')
    return df

def clean_birthdays(df):

    # do not modify in place

    # df = df.reset_index()
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

def fetch_quotes(spreadsheet_id: str, sheet_name: str, target_file: Optional[str] = None) -> pd.DataFrame():
    data = get_spreadsheet(spreadsheet_id, sheet_name)
    # if target_file is not None:
    #     data.to_csv(target_file)
    # data = clean_quotes(data) # clean AFTER saving because nathan's index gets saved and then reloaded and then the table grows without bound
    # TODO check and enforce column format
    #data.set_index(pd.util.hash_pandas_object(data), drop=False, inplace=True)
    return data

def fetch_birthdays(spreadsheet_id: str, sheet_name: str, target_file: Optional[str] = None) -> pd.DataFrame():
    data = get_spreadsheet(spreadsheet_id, sheet_name)
    # if target_file is not None:
    #     data.to_csv(target_file, index=False)
    # data = clean_birthdays(data)
    # TODO check and enforce column format
    # TODO make birthday column actual date objects
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
    