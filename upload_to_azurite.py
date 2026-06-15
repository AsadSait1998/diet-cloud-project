from pathlib import Path
import os

from azure.core.exceptions import ResourceExistsError
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


def upload_dataset_to_azurite(
    file_path: str = "All_Diets.csv",
    container_name: str = "datasets",
    blob_name: str = "All_Diets.csv",
) -> None:
    source = Path(file_path)

    if not source.exists():
        raise FileNotFoundError(
            f"Cannot upload missing file: {source}. "
            "Make sure All_Diets.csv is in the project root."
        )

    blob_service_client = BlobServiceClient.from_connection_string(
        AZURITE_CONNECTION_STRING
    )

    try:
        blob_service_client.create_container(container_name)
        print(f"Created container: {container_name}")
    except ResourceExistsError:
        print(f"Container already exists: {container_name}")

    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob=blob_name,
    )

    with source.open("rb") as data:
        blob_client.upload_blob(data, overwrite=True)

    print(f"Uploaded {source} to Azurite as {container_name}/{blob_name}")


if __name__ == "__main__":
    upload_dataset_to_azurite()
