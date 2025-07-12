#!/usr/bin/env python3
import logging
import datetime
import pymysql
import calendar
from datetime import date
from dotenv import load_dotenv
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

def third_wednesday(year, month):
    c = calendar.Calendar(firstweekday=calendar.MONDAY)
    monthcal = c.monthdayscalendar(year, month)
    wednesdays = [week[2] for week in monthcal if week[2] != 0]
    return date(year, month, wednesdays[2]) if len(wednesdays) >= 3 else None

def add_months(year, month, add):
    m = month - 1 + add
    new_year = year + m // 12
    new_month = (m % 12) + 1
    return new_year, new_month

# Determine contract months
today = date.today()
y0, m0 = today.year, today.month
this_month_third = third_wednesday(y0, m0)
if this_month_third and today <= this_month_third:
    M1_year, M1_month = y0, m0
    M1_date = this_month_third
else:
    y_next, m_next = add_months(y0, m0, 1)
    M1_year, M1_month = y_next, m_next
    M1_date = third_wednesday(M1_year, M1_month)

# M2, M4, M7 setup
y_m2, m_m2 = add_months(M1_year, M1_month, 1)
M2_date = third_wednesday(y_m2, m_m2)
y_m4, m_m4 = add_months(M1_year, M1_month, 3)
M4_date = third_wednesday(y_m4, m_m4)
y_m7, m_m7 = add_months(M1_year, M1_month, 6)
M7_date = third_wednesday(y_m7, m_m7)

# Month codes mapping
month_codes = {1:'F', 2:'G', 3:'H', 4:'J', 5:'K', 6:'M',
               7:'N', 8:'Q', 9:'U', 10:'V', 11:'X', 12:'Z'}

# Symbols for spot and futures
spot_symbol = 'VIX'
M1_symbol = f"VX/{month_codes.get(M1_month, '')}{str(M1_year)[-1]}"
M2_symbol = f"VX/{month_codes.get(m_m2, '')}{str(y_m2)[-1]}" if M2_date else None
M4_symbol = f"VX/{month_codes.get(m_m4, '')}{str(y_m4)[-1]}" if M4_date else None
M7_symbol = f"VX/{month_codes.get(m_m7, '')}{str(y_m7)[-1]}" if M7_date else None

logger.info(f"Spot Symbol: {spot_symbol}, M1 Symbol: {M1_symbol}, M2 Symbol: {M2_symbol}, M4 Symbol: {M4_symbol}, M7 Symbol: {M7_symbol}")

# Initialize prices
tickers = ['spot', 'm1', 'm2', 'm4', 'm7']
prices = dict.fromkeys(tickers, 0.0)

# Scrape VIX and futures via Selenium + BeautifulSoup
headers = []
rows_data = []

try:
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    url = "https://www.cboe.com/tradable_products/vix/vix_futures"
    logger.info(f"Loading page: {url}")
    driver.get(url)
    driver.implicitly_wait(10)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Save page for debugging
    with open("debug_page.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)

    driver.quit()

    table = soup.find('table')
    if not table:
        raise RuntimeError("Could not find futures table on page")

    headers = [th.get_text(strip=True).replace(' ', '_') for th in table.find_all('th')]
    logger.info(f"Headers detected: {headers}")

    for row in table.tbody.find_all('tr'):
        row_values = [td.get_text(strip=True) for td in row.find_all('td')]
        rows_data.append(row_values)

        symbol = row_values[0] if len(row_values) > 2 else ''
        last_str = row_values[2] if len(row_values) > 2 else '0'
        try:
            price_val = float(last_str.replace(',', ''))
        except ValueError:
            price_val = 0.0

        if symbol == spot_symbol:
            prices['spot'] = price_val
        elif symbol == M1_symbol:
            prices['m1'] = price_val
        elif symbol == M2_symbol:
            prices['m2'] = price_val
        elif symbol == M4_symbol:
            prices['m4'] = price_val
        elif symbol == M7_symbol:
            prices['m7'] = price_val

    logger.info(f"Fetched via Selenium → Spot: {prices['spot']}, M1: {prices['m1']}, M2: {prices['m2']}, M4: {prices['m4']}, M7: {prices['m7']}")
except Exception as e:
    logger.error(f"Error scraping VIX futures via Selenium: {str(e)}")

# Compute metrics
vix_price = prices['spot']
m1_price = prices['m1']
m2_price = prices['m2']
m4_price = prices['m4']
m7_price = prices['m7']

m1m2_ratio = ((m1_price - m2_price) * vix_price / m2_price) if m2_price != 0 else 0.0
m1m2_avg = (m1_price + m2_price) / 2.0
m4m7_avg = (m4_price + m7_price) / 2.0
slope = (m1m2_avg - m4m7_avg) * vix_price

logger.info(f"M1M2_RATIO: {m1m2_ratio}, M1M2_AVG: {m1m2_avg}, M4M7_AVG: {m4m7_avg}, SLOPE: {slope}")

# Database operations
def create_database_tables(cursor, headers):
    try:
        columns = []
        for header in headers:
            header_clean = f"`{header}`"
            columns.append(f'{header_clean} TEXT')

        create_table_sql = f'''
        CREATE TABLE IF NOT EXISTS datas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            {", ".join(columns)},
            timestamp DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        '''
        logger.debug(f"Create Table SQL: {create_table_sql}")
        cursor.execute(create_table_sql)

        cursor.execute("SHOW COLUMNS FROM datas;")
        existing_columns = [col['Field'] for col in cursor.fetchall()]
        for header in headers:
            if header not in existing_columns:
                cursor.execute(f"ALTER TABLE datas ADD COLUMN `{header}` TEXT;")

        if 'timestamp' not in existing_columns:
            cursor.execute("ALTER TABLE datas ADD COLUMN timestamp DATETIME;")
    except Exception as e:
        logger.error(f"Error creating/updating datas table: {str(e)}")

# DB connection and data insertion
try:
    db_config = {
        'host': os.getenv('DB_HOST'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'port': int(os.getenv('DB_PORT')),
        'database': os.getenv('DB_NAME'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }

    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()

    create_database_tables(cursor, headers)
    run_ts = datetime.datetime.now()

    for row in rows_data:
        placeholders = ', '.join(['%s'] * (len(row) + 1))
        columns_str = ', '.join([f"`{h}`" for h in headers] + ['timestamp'])
        sql = f"INSERT INTO datas ({columns_str}) VALUES ({placeholders})"
        cursor.execute(sql, row + [run_ts])

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vix_metrics (
            id INT AUTO_INCREMENT PRIMARY KEY,
            run_timestamp DATETIME NOT NULL,
            vix FLOAT NOT NULL,
            m1 FLOAT NOT NULL,
            m2 FLOAT NOT NULL,
            m4 FLOAT NOT NULL,
            m7 FLOAT NOT NULL,
            m1m2_ratio FLOAT NOT NULL,
            m1m2_avg FLOAT NOT NULL,
            m4m7_avg FLOAT NOT NULL,
            slope FLOAT NOT NULL
        );
    """)

    cursor.execute("""
        INSERT INTO vix_metrics
        (run_timestamp, vix, m1, m2, m4, m7, m1m2_ratio, m1m2_avg, m4m7_avg, slope)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        run_ts,
        vix_price,
        m1_price,
        m2_price,
        m4_price,
        m7_price,
        m1m2_ratio,
        m1m2_avg,
        m4m7_avg,
        slope
    ))

    conn.commit()
    logger.info("Inserted VIX data and metrics into database.")
except pymysql.MySQLError as err:
    logger.error(f"Database error: {str(err)}")
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()
