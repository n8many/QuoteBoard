quote_source = ""   # Worksheet ID from google sheets

# Main source of quotes, if quote_source is empty, file will not get updated
quote_sheet = "Quotes"
quote_file = "quotes.csv"

# If you'd like to only show quotes for the birthday person
enable_birthday_quotes = True
birthday_sheet = "Birthdays"
birthday_file = "birthdays.csv"

quote_frequency = 60  # in minutes
antirepeat_depth = 20  # number of times until repeat is allowed