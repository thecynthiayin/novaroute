"""Load the Kaggle internship opportunities dataset and import into NovaRoute database."""

import sys
from pathlib import Path
import kagglehub
from kagglehub import KaggleDatasetAdapter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "database"))
from seed import import_dataframe

# File inside the dataset
file_path = "internship.csv"

print("Downloading/loading dataset from Kaggle via kagglehub...")
loader = getattr(kagglehub, "dataset_load", getattr(kagglehub, "load_dataset", None))
df = loader(
    KaggleDatasetAdapter.PANDAS,
    "everydaycodings/internship-opportunities-dataset",
    file_path,
)

print(f"Dataset loaded successfully! Total records: {len(df)}")
print("\nFirst 5 records preview:")
for idx, row in df.head().iterrows():
    print(f"  {idx + 1}. {row.get('internship_title')} at {row.get('company_name')} ({row.get('location')})")

print("\nImporting technical internships into NovaRoute MySQL database...")
stats = import_dataframe(df, limit=25, seed=42, kind="kaggle")
print("Import result:", stats)
