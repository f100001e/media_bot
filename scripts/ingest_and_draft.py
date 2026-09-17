from ingest.sources import save_raw_items
from llm.draft import generate_for_unprocessed


def main():
    print("Starting content ingest...")

    try:
        save_raw_items()
        print("✓ Content ingest complete")
    except Exception as exc:
        print(f"✗ Content ingest failed: {exc}")
        return

    print("Generating drafts...")

    try:
        generate_for_unprocessed()
        print("✓ Draft generation complete")
    except Exception as exc:
        print(f"✗ Draft generation failed: {exc}")
        raise


if __name__ == "__main__":
    main()