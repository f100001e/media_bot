from ingest.sources import save_raw_items
from llm.draft import generate_for_unprocessed

if __name__ == "__main__":
    save_raw_items()
    generate_for_unprocessed()