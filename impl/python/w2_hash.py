import hashlib
import sys

CHUNK = 1024 * 1024


def main(path: str) -> None:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(CHUNK):
            digest.update(chunk)
    print(digest.hexdigest())


if __name__ == "__main__":
    main(sys.argv[1])
