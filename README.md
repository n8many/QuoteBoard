# QuoteBoard
Ever need to make sure the dumb things your friends/team/family have said will never be forgotten? This project is for you.

This is a simple webpage that will display a new quote from your list of quotes at a configurable time period.

To run the server run:

```
pip install -r requirements.txt
python quote_server.py
```

Then access the webpage via http://<ip_of_your_server>:8080

Settings on the quote page may be changed at http://<ip_of_your_server>:8080/settings.html

## The Database
The database the quote server uses is a Google sheet. This allows the sheet to be shared with multiple people (who perhaps don't have great knowledge of how to modify a database) and all contribute quotes. 

In order to access google sheets, you'll need to follow the steps [here](https://docs.gspread.org/en/latest/oauth2.html#enable-api-access-for-a-project) to create a Project and Service Account to access your quote database. Ensure your quote refresh period is not set too high, or you have too many devices, otherwise you may hit the rate limits for a Test Project.

In order to make sure the project can access the worksheet, you must do the following
* Add the credential file for your Service User as "credentials.json" to the root of the project directory
* Add the following information as "database.json" in the root of the project directory:
```
{
  "quote_source": "SHEET_ID_OF_YOUR_SHEET",
  "quote_sheet": "Quotes",
  "birthday_sheet": "Birthdays"
}
```
Currently access to sheets is required, but may be taken out in the future.

## The Quote Sheet Format
The quote sheet from your spreadsheet should have the following column format:
| Quote	| Who | Date | Context |
| ----- | --- | ---- | ------- |

The quote will be displayed in large text with the name below. The date and context are free text and may be used in the future.
