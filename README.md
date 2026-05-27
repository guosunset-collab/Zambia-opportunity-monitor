# Zambia Infrastructure Opportunity Intelligence Monitoring System

Cloud-first Python MVP for monitoring Zambia infrastructure-related business opportunities through GitHub Actions. The system collects candidate notices, filters for real procurement opportunities, scores relevance, deduplicates records in SQLite, and generates Markdown/HTML reports under `reports/`.

Email sending is intentionally disabled. GitHub Actions publishes the generated reports as workflow artifacts.

## MVP Coverage

- Government Procurement: ZPPA eGP and ZPPA main site
- Road & Transport: Road Development Agency and National Road Fund Agency
- Airport / Aviation: Zambia Airports Corporation
- PPP / Investment: Ministry of Finance / PPP signal source
- Donor-funded: World Bank Zambia procurement source
- Newspapers: Zambia Daily Mail
- Social Media: Facebook official-page early signals

Some sites use dynamic pages, access controls, or social-platform protections. Each source is isolated so one failure does not stop the daily report.

## Report Structure

Reports start with an Executive Brief:

- total new opportunities
- high priority items
- PPP signals
- newspaper findings
- donor-funded opportunities
- alerts requiring manual review

Detailed opportunities are grouped by source:

- Government Procurement (ZPPA / eGP)
- Road & Transport (RDA / NRFA / RTSA)
- Airport / Aviation (ZACL / Ministry)
- PPP / Investment
- Donor-funded
- Newspapers
- Social Media

## Filtering Rules

The MVP keeps candidates only when they contain at least one real opportunity signal:

- tender
- invitation for bids
- EOI
- expression of interest
- RFP
- RFQ
- procurement notice
- deadline
- closing date
- consultancy services
- works contract
- prequalification

It excludes common non-opportunities such as homepages, contact pages, training pages, public procurement act pages, airport services pages, general notices, currency notices, toll payment notices, and news articles without a deadline.

## Project Structure

```text
.
|-- main.py
|-- requirements.txt
|-- config.example.yaml
|-- storage.py
|-- scoring.py
|-- report.py
|-- logger.py
|-- parsers/
|   |-- html_parser.py
|   |-- pdf_parser.py
|   `-- ocr_parser.py
|-- scrapers/
|   |-- base.py
|   |-- government/
|   |-- ppp/
|   |-- donors/
|   |-- utilities/
|   |-- newspapers/
|   `-- social/
|-- database/
|-- logs/
|-- reports/
`-- .github/workflows/daily.yml
```

## Run Locally

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the monitor:

```bash
python main.py
```

Outputs:

- SQLite database: `database/opportunities.sqlite3`
- structured log: `logs/monitor.log`
- Markdown report: `reports/zambia_infrastructure_report_YYYY-MM-DD.md`
- HTML report: `reports/zambia_infrastructure_report_YYYY-MM-DD.html`

## Configure Sources

Create a local config if you want to customize sources:

```bash
cp config.example.yaml config.yaml
```

On Windows PowerShell:

```powershell
Copy-Item config.example.yaml config.yaml
```

Edit `config.yaml` to enable, disable, or add source URLs. Keep `email.enabled` as `false`; cloud delivery is handled by GitHub Actions artifacts.

## Deploy On GitHub Actions

1. Push this project to a GitHub repository.
2. Confirm `.github/workflows/daily.yml` is present.
3. Open the repository in GitHub.
4. Go to `Actions` and enable workflows if prompted.
5. Run `Zambia Infrastructure Opportunity Intelligence` manually once with `workflow_dispatch`.
6. Download the `zambia-infrastructure-reports` artifact from the completed run.

The workflow runs daily at:

```yaml
cron: "0 7 * * *"
```

That is 07:00 UTC, equivalent to 09:00 in Zambia / Africa Lusaka time.

## GitHub Actions Steps

The workflow performs:

- checkout
- setup Python 3.11
- install requirements
- run `python main.py`
- upload `reports/` as an artifact

## Expansion Roadmap

- Add Playwright extraction for dynamic procurement pages.
- Add a confirmed dedicated PPP Unit/Council endpoint.
- Add newspaper e-paper PDF discovery and OCR processing.
- Add Facebook Graph API mode using page tokens.
- Add more donor sources: AfDB, JICA, EU, UN Procurement, MCC.
- Add richer entity extraction for tender numbers, deadlines, and publication dates.
- Add optional AI-assisted summarization/scoring.
