# Boomkat End of Year in machine-readable format


This is a collection of the end of year lists from [Boomkat](https://boomkat.com/) in a machine-readable format.

The lists are available as SQLite database with a joined dump and individual chart CSV files:

- [boomkat.db](boomkat.db) (SQLite database)
- [boomkat.db.csv](boomkat.db.csv) (CSV file)
- [`csv/raw/`](csv/raw/) (CSV files for each chart)

## Code

The code is a few years old but seems to work still. It relies on Selenium and an undetected Chromedriver. If you want to re-create this database, you can run the following commands:

```bash
# Install dependencies
pip install -r requirements.txt
python boomkat.py
```