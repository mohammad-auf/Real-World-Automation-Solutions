import os
import csv
from dotenv import load_dotenv
import agentql
from playwright.sync_api import sync_playwright

# Load environment variables
load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
AGENTQL_API_KEY = os.getenv("AGENTQL_API_KEY")
os.environ["AGENTQL_API_KEY"] = AGENTQL_API_KEY

INITIAL_URL = "https://www.idealist.org/login"
URL = "https://www.idealist.org/en/jobs"
CSV_FILE = "jobs.csv"

Email_input_query = """{
    login_form {
        email_input
    }
}"""

Password_input_query = """{
    login_form {
        password_input
        login_form_submit_button
    }
}"""

def login():
    with sync_playwright() as playwright:
        with playwright.chromium.launch(headless=False) as browser:
            page = agentql.wrap(browser.new_page())
            page.goto(INITIAL_URL)

            response = page.query_elements(Email_input_query)
            response.login_form.email_input.fill(EMAIL)
            page.wait_for_timeout(100)

            password_response = page.query_elements(Password_input_query)
            password_response.login_form.password_input.fill(PASSWORD)
            page.wait_for_timeout(100)
            password_response.login_form.login_form_submit_button.click()

            page.wait_for_page_ready_state()
            page.context.storage_state(path="idealist_login.json")
            page.wait_for_timeout(3000)

def save_job_row(job, file_exists):
    """Save a single job row to CSV"""
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=job.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(job)

def extract_and_save_jobs(page):
    """Extract job data from one page and save each job immediately"""
    page.wait_for_selector('[data-qa-id="search-result"]')
    job_cards = page.query_selector_all('[data-qa-id="search-result"]')

    for card in job_cards:
        job_title = card.query_selector('[data-qa-id="search-result-link"]')
        company = card.query_selector('h4 .sc-1pfcxqe-0')
        details = card.query_selector_all('[data-size="micro"] span.sc-wi6wdc-2')
        posted_time = card.query_selector('.sc-48d7r9-2')
        job_url = card.query_selector('a.sc-9gxixl-5')

        job = {
            "Title": job_title.inner_text() if job_title else "N/A",
            "Company": company.inner_text() if company else "N/A",
            "Work Type": details[0].inner_text() if len(details) > 0 else "N/A",
            "Location": details[1].inner_text() if len(details) > 1 else "N/A",
            "Job Type": details[2].inner_text() if len(details) > 2 else "N/A",
            "Posted": posted_time.inner_text() if posted_time else "N/A",
            "Job URL": "https://www.idealist.org" + job_url.get_attribute("href") if job_url else "N/A"
        }

        save_job_row(job, file_exists=os.path.exists(CSV_FILE))

def main():
    if not os.path.exists('idealist_login.json'):
        print("No login state found. Logging in...")
        login()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context(storage_state="idealist_login.json")
        page = agentql.wrap(context.new_page())
        page.goto(URL)
        page.wait_for_timeout(2000)

        while True:
            print("Scraping current page...")
            extract_and_save_jobs(page)

            next_button = page.query_selector('[data-qa-id="pagination-link-next"]')
            if next_button and "disabled" not in next_button.get_attribute("class"):
                next_button.click()
                page.wait_for_timeout(3000)
                page.wait_for_selector('[data-qa-id="search-result"]')
            else:
                break

        browser.close()
        print(f"All data saved to {CSV_FILE}")

if __name__ == "__main__":
    main()
