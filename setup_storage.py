"""Create the private property-file bucket before serving requests."""

import os

from infrai_storage import InfraiStorage


def main() -> None:
    bucket = os.environ.get("PROPERTY_FILES_BUCKET", "property-private-files")
    InfraiStorage.from_environment().create_bucket(bucket)
    print(f"Bucket ready: {bucket}")


if __name__ == "__main__":
    main()
