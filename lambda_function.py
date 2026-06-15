from datetime import datetime, timezone
from pathlib import Path
import io
import json
import os

import pandas as pd
from azure.storage.blob import BlobServiceClient


AZURITE_CONNECTION_STRING = os.getenv(
    "AZURITE_CONNECTION_STRING",
    "DefaultEndpointsProtocol=http;"
    "AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    "QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;"
    "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;",
)

CONTAINER_NAME = os.getenv("AZURITE_CONTAINER_NAME", "datasets")
BLOB_NAME = os.getenv("AZURITE_BLOB_NAME", "All_Diets.csv")
NOSQL_OUTPUT_DIR = Path(os.getenv("NOSQL_OUTPUT_DIR", "simulated_nosql"))


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]

    rename_map = {
        "Protein (g)": "Protein(g)",
        "Carbs (g)": "Carbs(g)",
        "Fat (g)": "Fat(g)",
        "Diet type": "Diet_type",
        "Recipe name": "Recipe_name",
        "Cuisine type": "Cuisine_type",
    }
    df = df.rename(columns=rename_map)

    required = ["Diet_type", "Protein(g)", "Carbs(g)", "Fat(g)"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns from blob CSV: {missing}")

    numeric_cols = ["Protein(g)", "Carbs(g)", "Fat(g)"]

    for col in numeric_cols:
        df.loc[:, col] = pd.to_numeric(df[col], errors="coerce")

    df.loc[:, numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
    df.loc[:, numeric_cols] = df[numeric_cols].fillna(0)

    df.loc[:, "Diet_type"] = (
        df["Diet_type"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
        .str.title()
    )

    return df


def process_nutritional_data_from_azurite() -> str:
    blob_service_client = BlobServiceClient.from_connection_string(
        AZURITE_CONNECTION_STRING
    )

    blob_client = blob_service_client.get_blob_client(
        container=CONTAINER_NAME,
        blob=BLOB_NAME,
    )

    stream = blob_client.download_blob().readall()
    df = pd.read_csv(io.BytesIO(stream))
    df = clean_dataset(df)

    avg_macros = (
        df.groupby("Diet_type")[["Protein(g)", "Carbs(g)", "Fat(g)"]]
        .mean()
        .round(2)
        .reset_index()
    )

    result = {
        "processed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "storage": "Azurite local Blob Storage emulator",
            "container": CONTAINER_NAME,
            "blob": BLOB_NAME,
        },
        "simulated_database": "Local JSON file standing in for Cosmos DB or NoSQL",
        "average_macros_by_diet": avg_macros.to_dict(orient="records"),
    }

    NOSQL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = NOSQL_OUTPUT_DIR / "results.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return f"Data processed and stored successfully at {output_path}"


if __name__ == "__main__":
    print(process_nutritional_data_from_azurite())
