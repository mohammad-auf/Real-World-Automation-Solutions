# 📈 VIX Futures Data Pipeline using Django, Selenium, and MySQL

This project automates the extraction, storage, and visualization of VIX Futures market data from the [CBOE website](https://www.cboe.com/tradable_products/vix/vix_futures/), using a robust ETL (Extract, Transform, Load) pipeline deployed on a Hostinger VPS.

---

## 🚀 Features

- **Automated Scraping**: Market data scraped every hour from 8:00 AM to 5:00 PM EST using Selenium & BeautifulSoup.
- **MySQL Storage**: All futures data and calculated metrics are stored in a structured MySQL database.
- **Expiry-Aware Analysis**: Automatically computes values for M1, M2, M4, and M7 futures contracts based on third Wednesdays.
- **Custom Metrics**: Computes metrics like VIX slope, M1/M2 ratios, and more.
- **Django-Powered Visualization**: Frontend built using Django to display a rolling 30-day chart, color-coded by Expiry Date.
- **Deployable**: Hosted on a VPS (Hostinger) with full backend/frontend integration.

---

## 📊 Technologies Used

- **Python 3**
- **Selenium + BeautifulSoup**
- **Django Framework**
- **MySQL Database**
- **ChromeDriver via `webdriver-manager`**
- **Hostinger VPS for deployment**

---

## 📦 How It Works

1. **Scraping (`main.py`)**:
   - Uses Selenium to load dynamic content from the CBOE VIX Futures page.
   - Extracts the full table and computes contract-specific symbols and custom metrics.
   - Saves both raw data and calculated metrics in MySQL.

2. **Backend**:
   - Django-based admin panel and frontend fetch data from the database.
   - Periodic cron job or task scheduler invokes the script hourly.

3. **Frontend**:
   - Interactive chart with a 30-day rolling view for each expiry contract.
   - Contracts are distinguished by color for better analysis.

---

## ⚙️ Setup Instructions

1. Clone the repo.
2. Install requirements:

   ```bash
   pip install selenium pymysql beautifulsoup4 webdriver-manager
