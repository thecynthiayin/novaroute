# Dataset provenance

Source: [Internship Opportunities Dataset](https://www.kaggle.com/datasets/everydaycodings/internship-opportunities-dataset), publisher `everydaycodings`.

The public ZIP was downloaded during implementation on 2026-09-20 Asia/Bangkok. It contained **`internship.csv`, 6,485 rows**, with exactly these headers:

`internship_title`, `company_name`, `location`, `start_date`, `duration`, `stipend`.

The first record was Java Development at SunbaseData, Work From Home, Immediately, 6 Months, ₹ 30,000 /month. The source does **not** provide descriptions, skills, application deadlines, or stable row IDs. Kaggle's public dataset-list API reported **CC0: Public Domain**, last updated `2023-11-17T16:43:29.327Z`. An explicit numeric dataset version was not available in the inspected response. License metadata should be checked again when downloading a newer revision. Source rows are not redistributed here.

Download manually from the dataset page, or use the Kaggle CLI with your own configuration:

```bash
kaggle datasets download -d everydaycodings/internship-opportunities-dataset -p work/kaggle --unzip
python database/seed.py --csv work/kaggle/internship.csv --limit 25 --seed 42
```

If Kaggle prompts for login/consent, complete it yourself and place the extracted CSV at `database/data/internship.csv`. Never commit a Kaggle token. The public download endpoint worked here; this is not a guarantee of future anonymous access.

The importer logs selected header mappings; it normalizes punctuation/case and accepts aliases in `database/seed.py`. `--mapping path.json` allows an explicit mapping such as `{"title":"Position","company":"Organization"}`. Title and company are required. Empty/invalid/nontechnical rows are skipped and counted. Invalid skill JSON is rejected, never evaluated. UTF-8 BOM is supported; encoding failures stop with a useful message so the operator can convert the source deliberately.

Without source skills, the importer performs conservative vocabulary matching against title/description. It records `skills_inferred=true`; no technologies are invented from generic titles. Without description, it assembles a clearly labelled historical summary from source attributes and records `description_assembled=true`. Original company and stipend text are stored in provenance. Only unambiguous INR monthly amounts/ranges are parsed into decimals; all other stipend text remains unparsed provenance. Dates are never extended into the future, and `Immediately` is not interpreted as a deadline.

Stable source IDs, when present, or a deterministic source-content hash enforce idempotence. Existing records are skipped, including soft-deleted or user-edited records; updates are not silently applied. The account owning imports is **Nova Labs · Demo Employer**, which explicitly does not represent source companies. These are historical demonstration records, not current verified openings.

Actual import verification: seed 42 selected **25** usable technical records, skipped **65**, and reported **0** updates. A second identical run imported **0**, reported **25** duplicates and **65** skips. The run used the isolated MySQL test database.

`database/data/synthetic-internships.csv` is an entirely separate, locally authored set of **25 fictional technical internships** used by `--demo`. It is not Kaggle data. Its descriptions and requirements are fictional demo content, with stable `synthetic-01`…`synthetic-25` IDs and no invented real-world employer claims. Seed student names and `.test` addresses are fictional. Production rejects seed commands and seed account authentication.
