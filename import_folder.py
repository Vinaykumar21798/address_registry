import os
import requests
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

API_URL = "http://127.0.0.1:8000/upload"

PDF_FOLDER = "sample_pdfs"

processed = 0
duplicates = 0
failed = 0


for filename in os.listdir(PDF_FOLDER):

    if not filename.lower().endswith(".pdf"):
        continue

    filepath = os.path.join(
        PDF_FOLDER,
        filename
    )

    print(f"\nUploading: {filename}")

    try:

        with open(filepath, "rb") as f:

            response = requests.post(
                API_URL,
                files={
                    "file": (
                        filename,
                        f,
                        "application/pdf"
                    )
                }
            )

        if response.status_code == 200:

            data = response.json()

            if data.get("status") == "failed":

                failed += 1

                print(
                    f"✗ Failed: {filename}"
                )

                print(
                    f"  Reason: {data.get('reason')}"
                )

            else:

                processed += 1

                print(
                    f"✓ Processed: {filename}"
                )

        elif response.status_code == 409:

            duplicates += 1

            try:
                detail = response.json().get(
                    "detail",
                    {}
                )

                print(
                    f"✓ Duplicate: {filename}"
                )

                print(
                    f"  Existing Document ID: "
                    f"{detail.get('document_id')}"
                )

            except Exception:

                print(
                    f"✓ Duplicate: {filename}"
                )

        else:

            failed += 1

            print(
                f"✗ Failed: {filename}"
            )

            print(
                f"  HTTP Status: "
                f"{response.status_code}"
            )

    except Exception as e:

        failed += 1

        print(
            f"✗ Error: {filename}"
        )

        print(
            f"  {str(e)}"
        )


print("\n======================")
print("IMPORT SUMMARY")
print("======================")

print(
    f"Processed : {processed}"
)

print(
    f"Duplicates: {duplicates}"
)

print(
    f"Failed    : {failed}"
)

total = (
    processed +
    duplicates +
    failed
)

print(
    f"Total Files: {total}"
)