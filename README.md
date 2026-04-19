Columbia University Course Evaluation & Advising Toolkit
======================================================

A comprehensive suite of Python tools designed to scrape, aggregate, and
visualize Columbia University course evaluations, CULPA professor
reviews, and academic bulletin data.

This project includes automated scrapers for legacy APIs,
Playwright-based web scrapers, and an interactive Streamlit dashboard
for exploring the data.

SECURITY WARNING \-\-\-\-\-\-\-\-\-\-\-\-\-\-\-- Before you push this to
GitHub, you MUST ensure your authentication files (.columbia_token,
.columbia_cookie, .webui_secret_key) are added to a .gitignore file. If
you upload these to a public repository, anyone on the internet can
access your Columbia account.

FEATURES \-\-\-\-\-\-\-- \* Course Evaluation Downloader: Bypasses
legacy API constraints to bulk-download official course evaluation PDFs
across multiple terms and departments. \* CULPA Lore Scraper: Extracts
qualitative student reviews from the Columbia Undergraduate Listing of
Professorial Abilities (CULPA) website. \* Bulletin Advising Scraper:
Pulls department and course information from the official Columbia
College Bulletin to build a complete academic reference text. \*
Interactive Dashboard: A clean, searchable Streamlit web interface to
filter courses, compare professors, and view grade/workload
distributions.

REPOSITORY STRUCTURE \-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-- \* app.py :
The main Streamlit dashboard. Reads from eval_database.csv to display
interactive charts, distributions, and filters. \* new_downloader.py :
The optimized, fast-edition evaluation downloader. Uses connection
pooling and caching to fetch PDFs from the Vergil/EvalKit API. \*
columbia_eval_downloader.py : The standard fallback script for
downloading EvalKit PDFs. \* culpa_scraper.py : A headless Playwright
scraper that iterates through CULPA professor IDs, cleans out junk UI
text, and saves narrative reviews. \* AdvisingScraper.py : Uses
BeautifulSoup to parse the Columbia Bulletin and aggregate departmental
requirements into a single .txt knowledge base. \* eval_database.csv :
The processed, structured dataset containing numeric scores, workload
metrics, and written comments ready for the dashboard.

Ignored Files (Local Use Only) The following files are required for the
scripts to run but MUST NOT be uploaded to GitHub: \* .columbia_token &
.columbia_cookie : Your personal Vergil/EvalKit session credentials. \*
.webui_secret_key : Secrets for the dashboard interface.

INSTALLATION & SETUP \-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-- 1. Clone
the repository git clone
https://github.com/yourusername/columbia-eval-toolkit.git cd
columbia-eval-toolkit

2\. Install dependencies This project requires several third-party
libraries: pip install requests beautifulsoup4 streamlit pandas plotly
playwright

3\. Install Playwright Browsers (Required for CULPA) playwright install
chromium

4\. Set up Credentials Create local text files named .columbia_token and
.columbia_cookie in the root directory. Paste your active Bearer token
and Session Cookie into these files respectively.

USAGE \-\-\-\-- 1. Scraping Official Evaluations To bulk-download the
official PDFs, run the optimized downloader. You can adjust the batch
size by setting an environment variable: \# Windows:
\$env:BATCH_SIZE=\"500\"; python new_downloader.py \# Mac/Linux:
BATCH_SIZE=500 python new_downloader.py

2\. Scraping CULPA Reviews To fetch the qualitative \"lore\" on
professors: python culpa_scraper.py

3\. Fetching Advising Data To pull the latest Columbia College Bulletin
data: python AdvisingScraper.py

4\. Running the Dashboard Once your data is extracted and
eval_database.csv is populated, launch the UI: python -m streamlit run
app.py
