import logfire
from unstructured.partition.auto import partition

def parse_office(file_path: str):
    with logfire.span("Office Document Parsing", filename=file_path):
        try:
            elements = partition(filename=file_path)
            full_text = "\n".join([str(ele) for ele in elements])

            if not full_text.strip():
                logfire.warning("⚠️ Unstructured has return empty text for {full_text}")
            else:
                logfire.info("✔️ Successfully parse {len(full_text)} characters")

            return full_text
        except Exception as e:
            logfire.error("❌ Office Parsing Fail, {e}")
            return e