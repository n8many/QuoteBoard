from typing import Optional

import gspread
import pandas as pd

def get_spreadsheet(spreadsheet_id: str, sheet_name: str) -> pd.DataFrame():
    # Log in, get workbook, get spreadsheet, save data, return as DataFrame
    gc = gspread.service_account('credentials.json')
    spreadsheet = gc.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(sheet_name)
    # TODO may need some sanitization of stray data
    rows = worksheet.get_all_records()
    data = pd.DataFrame(rows)
    return data

def update_quotes(spreadsheet_id: str, sheet_name: str, target_file: Optional[str]) -> pd.DataFrame():
    data = get_spreadsheet(spreadsheet_id, sheet_name)
    # TODO check and enforce column format
    data.set_index(pd.util.hash_pandas_object(data), drop=False, inplace=True)
    if target_file is not None:
        data.to_csv(target_file)
    return data

def update_birthdays(spreadsheet_id: str, sheet_name: str, target_file: Optional[str]) -> pd.DataFrame():
    data = get_spreadsheet(spreadsheet_id, sheet_name)
    # TODO check and enforce column format
    # TODO make birthday column actual date objects
    data.reset_index()
    if target_file is not None:
        data.to_csv(target_file, index=False)
    return data

if __name__ == "__main__":
    from config import quote_source, quote_sheet, quote_file, enable_birthday_quotes, birthday_sheet, birthday_file
    quotes = update_quotes(quote_source, quote_sheet, quote_file)
    print(quotes)

    if enable_birthday_quotes:
        birthdays = update_birthdays(quote_source, birthday_sheet, birthday_file)
        print(birthdays)