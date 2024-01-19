from bs4 import BeautifulSoup
import re
import random
import urllib.parse
import time
import pandas as pd
import os
import math

from undetected_chromedriver import Chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from tqdm import tqdm

CSV_FOLDER = 'csv/'
HTML_FOLDER = 'html/'

class ChartList():

    # contains charts and charts_meta for a given year/type

    def __init__(self, type = 'eoy', year = 2022, selenium_instance = None):

        self.type = type
        self.year = year

        self.charts_meta = []
        self.charts = []

        if type == 'eoy':
            self.url = f'https://boomkat.com/charts/boomkat-end-of-year-charts-{str(self.year)}/'

        self.drivers = []

        if selenium_instance is not None:
            self.drivers.append(selenium_instance)

        self.request_site()

        if not self.local_copy:
            self.save_html()
        self.create_bs()
        self.collect_chart_list_meta()


    def add_selenium_driver(self):
        self.drivers.append(Chrome())


    def request_site(self):

        print(f'Requesting {self.url}')

        # check whether theres a local copy available
        if f'{self.url.replace("/", "___")}.html' in os.listdir(HTML_FOLDER):
            print('\tLocal copy found')
            with open(f'{HTML_FOLDER}{self.url.replace("/", "___")}.html', 'r') as f:
                self.response = f.read()
            self.local_copy = True
        else:

            if len(self.drivers) == 0:

                self.add_selenium_driver()

            self.drivers[0].get(self.url)

            WebDriverWait(self.drivers[0], 120).until(EC.presence_of_element_located((By.CLASS_NAME, 'sb-wrapper')))

            # check status code
            assert 'Boomkat' in self.drivers[0].title

            print('\tRequest successful')

            # get response
            self.response = self.drivers[0].page_source

            self.local_copy = False

    def save_html(self):
        # save html to file

        # create folder if it doesn't exist
        if not os.path.exists(HTML_FOLDER):
            os.makedirs(HTML_FOLDER)
        with open(f'{HTML_FOLDER}{self.url.replace("/", "___")}.html', 'w') as f:
            f.write(self.response)

    def create_bs(self):

        self.bs = BeautifulSoup(self.response, 'lxml')

    def collect_chart_list_meta(self):

        # get all links that point to self.url/[0-9]
        charts_links = self.bs.find_all('a', href=re.compile(f'{self.url.split("-")[-1]}[0-9]'))

        for link in charts_links:

            id = link.get('href').split('/')[-1]

            curator = None

            if link.find() is not None:

                curator = link.find().get('alt')
                curator = curator.replace(str(self.year), '').replace(':', '').strip()

                curator_id = curator.lower().replace(' ', '_').replace('-', '_').replace('.', '_').replace('(', '').replace(')', '')

                # @TODO for curator_id, ignore labels in parentheses (), after /

                try:
                    img_url = link.find().get('src')
                except:
                    img_url = None

            url = link.get('href')

            self.charts_meta.append({'chart_id': id, 'curator': curator, 'curator_id': curator_id, 'url': url, 'img_url': img_url, 'year': self.year, 'type': self.type})


    def request_charts(self):

        # if len(self.drivers) < 1:
        #    # add more drivers to avoid cloudflare blocking
        #    for i in range(1):
        #        self.add_selenium_driver()

        # check the number of html files in HTML_FOLDER that have the year in the name
        # if there are more than 10, then we assume that all charts have been downloaded
        dl_ratio = len([f for f in os.listdir(HTML_FOLDER) if str(self.year) in f]) / len(self.charts_meta)

        if dl_ratio > 1:
            dl_ratio = 1

        for i, chart in tqdm(enumerate(self.charts_meta)):

            # random sleep to avoid cloudflare blocking
            time.sleep(math.sqrt(abs(math.log(dl_ratio+0.001)*100)))

            # every 10 charts, wait for a longer time
            if i % 10 == 0 and i != 0:
                time.sleep(math.sqrt(abs(math.log(dl_ratio + 0.001) * 100)))

            # retry 3 times in case of error
            for j in range(3):

                try:
                    self.charts.append(Chart(chart, selenium_instance = random.choice(self.drivers)))
                    break
                except Exception as e:

                    # if selenium error
                    if 'selenium' in str(e):
                        print(f'Error while requesting chart {chart["id"]}: {e}')
                        print(f'Error in chart ID {i} (retry {j})')
                        print(f'Waiting for a longer time...')
                        time.sleep(math.sqrt(abs(math.log(dl_ratio + 0.001) * 100))*100)
                    else:
                        continue

        # close all drivers
        for driver in self.drivers:
            try:
                driver.close()
                driver.quit()
            except:
                pass

class Chart():

    def __init__(self, metadata, selenium_instance = None):

        self.metadata = metadata

        self.url = urllib.parse.urljoin('https://boomkat.com/', self.metadata['url'])

        self.items = []

        self.driver = selenium_instance

        if self.driver is None:
            self.driver = Chrome()

        self.request_site()

        if not self.local_copy:
            self.save_html()

        self.create_bs()

        self.collect_chart_items()

        self.to_csv()


    def to_csv(self):

        # if CSV_FOLDER/year does not exist, create it
        if not os.path.exists(CSV_FOLDER+'raw/'+str(self.metadata['year'])):
            os.makedirs(CSV_FOLDER+'raw/'+str(self.metadata['year']))

        # save chart items to csv using pandas
        pd.DataFrame.from_records(self.items).to_csv(f'{CSV_FOLDER}raw/{self.metadata["year"]}/{self.metadata["curator"].lower().replace(" ", "_").replace("/", "___")}.csv')


    def request_site(self):

        print(f'Requesting {self.url}')

        # check whether theres a local copy available
        if f'{self.url.replace("/", "___")}.html' in os.listdir(HTML_FOLDER):
            print('\tLocal copy found')
            with open(f'{HTML_FOLDER}{self.url.replace("/", "___")}.html', 'r') as f:
                self.response = f.read()
            self.local_copy = True
        else:

            self.driver.get(self.url)

            WebDriverWait(self.driver, 120).until(EC.presence_of_element_located((By.CLASS_NAME, 'sb-wrapper')))

            # check status code
            assert 'Boomkat' in self.driver.title

            # get response
            self.response = self.driver.page_source

            self.local_copy = False

    def save_html(self):
        if not os.path.exists(HTML_FOLDER):
            os.makedirs(HTML_FOLDER)
        with open(f'{HTML_FOLDER}{self.url.replace("/", "___")}.html', 'w') as f:
            f.write(self.response)

    def create_bs(self):

        self.bs = BeautifulSoup(self.response, 'lxml')

    def collect_chart_items(self):

        chart_items = self.bs.find_all('div', class_='chart-item')

        for item in chart_items:

            item_id = None
            rank = None
            release = None
            artist = None
            title_full = None
            label = None
            description = None
            boomkat_url = None
            img_url = None

            # rank
            try:
                rank = int(item.find(class_='chart-item-bauble').get_text().strip())
            except:
                pass


            # description
            try:
                description = item.find(class_='chart-item-review').get_text().strip()
            except:
                pass

            # boomkat_url
            try:
                boomkat_url = item.find(class_='chart-item-title').find('a').get('href')
            except:
                pass

            # full title text

            try:
                title_full = item.find(class_='chart-item-title').get_text().strip()

            except:
                pass


            # release
            try:
                release = title_full

                # from title, extract artist and track
                if re.search('\s—\s', release) is not None:
                    artist = release.split('—')[0].strip()
                    release = release.split('—')[1].strip()



            except:
                pass

            # label from release
            try:
                # extract label from title
                if '(' in release and boomkat_url is not None:
                    label = release.split('(')[1].replace(')', '').strip()
            except:
                pass


            # remove label from release
            try:
                if label is not None:
                    release = release.replace(f'({label})', '').strip()
            except:
                pass


            # img
            try:
                img_url = item.find(class_='chart-item-image').find('img').get('src')
            except:
                pass

            # item_id

            # id

            try:
                if boomkat_url is not None:
                    item_id = boomkat_url.split('/')[-1].strip()
                elif release is not None:
                    item_id = re.sub(r'[^a-z0-9]|[^\x00-\x7F]+', '', release.lower().strip())
                elif title_full is not None:
                    item_id =  re.sub(r'[^a-z0-9]|[^\x00-\x7F]+', '', title_full.lower().strip())
                else:
                    raise Exception('No item ID found')
            except:
                item_id = self.metadata['chart_id'] + '_' + str(rank)

            # add item to list
            self.items.append({

                'item_id': item_id,
                'rank': rank,
                'artist': artist,
                'release': release,
                'title_full': title_full,
                'label': label,
                'description': description,
                'boomkat_url': boomkat_url,
                'img_url': img_url,
                'chart_id': self.metadata['chart_id'],
                'chart_curator': self.metadata['curator'],
                'chart_year': self.metadata['year'],
                'chart_url': self.url

            })



if __name__ == '__main__':

    def dict_set (d, key):
        return [d for d in dict((v[key], v) for v in d).values()]

    # if CSV_FOLDER and/or HTML_FOLDER do not exist, create them
    if not os.path.exists(CSV_FOLDER):
        os.makedirs(CSV_FOLDER)
    if not os.path.exists(HTML_FOLDER):
        os.makedirs(HTML_FOLDER)

    # instantiate selenium driver
    driver = Chrome()

    years = [2023]

    eoys = []

    for year in years:

        print(f'Collecting charts for {year}')

        chartlist = ChartList(type = 'eoy', year = year, selenium_instance = driver)

        chartlist.request_charts()

        # insert chartlist metadata into database
        #conn.executemany('INSERT INTO chartlists_raw (year, type, curator, url, img_url) VALUES (:year, :type, :curator, :url, :img_url)', [(c['year'], c['type'], c['curator'], c['url'], c['img_url'], ) for c in chartlist.charts_meta])

        # insert chart items into database
        #conn.executemany('INSERT INTO items_raw (year, type, curator, rank, title, description, boomkat_url, img_url) VALUES (:year, :type, :curator, :rank, :title, :description, :boomkat_url, :img_url)', [(c.metadata['year'], c.metadata['type'], c.metadata['curator'], item['rank'], item['title'], item['description'], item['boomkat_url'], item['img_url'],) for c in chartlist.charts for item in c.items])

        #conn.commit()

        eoys.append(chartlist)



    # store all in database

    # connect to sqlite database
    import sqlite3
    conn = sqlite3.connect('boomkat.db')
    cur = conn.cursor()

    # create curators table if it does not exist

    cur.execute("""
        CREATE TABLE IF NOT EXISTS curators (
            id text PRIMARY KEY,
            name TEXT
        );
        """)

    # create charts table if it does not exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS charts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            curator_id text,
            year INTEGER,
            type TEXT,
            url TEXT,
            FOREIGN KEY (curator_id) REFERENCES curators(id)
        );
        """)

    # create items table if it does not exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id text PRIMARY KEY,
            artist TEXT,
            release TEXT,
            label TEXT,
            title_full TEXT,
            description TEXT,
            boomkat_url TEXT,
            img_url TEXT
        );
        """)

    # create chart_items table if it does not exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chart_id INTEGER,
            item_id text,
            rank INTEGER,
            FOREIGN KEY (chart_id) REFERENCES charts(id),
            FOREIGN KEY (item_id) REFERENCES items(id)
        );
        """)

    # add charts_items constraint
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS chart_items_unique ON chart_items (chart_id, item_id);
        """)

    # get all curators
    curators = [{'id': chart.metadata['curator_id'],
                 'name': chart.metadata['curator']} for eoy in eoys for chart in eoy.charts]

    # add curators to database, do nothin if id value already exists in table
    cur.executemany('INSERT OR IGNORE INTO curators (id, name) VALUES (:id, :name)', [(c['id'], c['name'], ) for c in curators])


    # get all charts
    charts = [{'id': chart.metadata['chart_id'],
                'curator_id': chart.metadata['curator_id'],
                'year': chart.metadata['year'],
                'type': chart.metadata['type'],
                'url': chart.url} for eoy in eoys for chart in eoy.charts]

    # add charts to database, do nothin if id value already exists in table
    cur.executemany('INSERT OR IGNORE INTO charts (id, curator_id, year, type, url) VALUES (:id, :curator_id, :year, :type, :url)', [(c['id'], c['curator_id'], c['year'], c['type'], c['url'], ) for c in charts])

    # get all items
    items = [{'id': item['item_id'],
                'artist': item['artist'],
                'release': item['release'],
                'label': item['label'],
                'title_full': item['title_full'],
                'description': item['description'],
                'boomkat_url': item['boomkat_url'],
                'img_url': item['img_url']} for eoy in eoys for chart in eoy.charts for item in chart.items]

    # add items to database, do nothin if id value already exists in table
    cur.executemany('INSERT OR IGNORE INTO items (id, artist, release, label, title_full, description, boomkat_url, img_url) VALUES (:id, :artist, :release, :label, :title_full, :description, :boomkat_url, :img_url)', [(c['id'], c['artist'], c['release'], c['label'], c['title_full'], c['description'], c['boomkat_url'], c['img_url'], ) for c in items])

    # get all chart_items
    chart_items = [{'chart_id': chart.metadata['chart_id'],
                    'item_id': item['item_id'],
                    'rank': item['rank']} for eoy in eoys for chart in eoy.charts for item in chart.items]

    # add chart_items to database, do nothin if id value already exists in table
    cur.executemany('INSERT OR IGNORE INTO chart_items (chart_id, item_id, rank) VALUES (:chart_id, :item_id, :rank)', [(c['chart_id'], c['item_id'], c['rank'], ) for c in chart_items])

    conn.commit()

