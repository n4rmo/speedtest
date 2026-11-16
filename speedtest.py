import argparse
from http.client import HTTPException
import sys
from time import perf_counter
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


REQUEST_COUNT = 10
CHUNK_SIZE = 64 * 1024
TIMEOUT_SECONDS = 30


def http_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError
        parsed.port
    except ValueError:
        raise argparse.ArgumentTypeError("Нужен корректный URL с http:// или https://") from None
    return value


def download(url: str) -> tuple[int, float]:
    request = Request(url, headers={
        "User-Agent": "SequentialSpeedTest/1.0",
        "Accept-Encoding": "identity",
        "Cache-Control": "no-cache",
    })
    downloaded = 0
    started = perf_counter()
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        while chunk := response.read(CHUNK_SIZE):
            downloaded += len(chunk)

        length = response.getheader("Content-Length")
        if length is not None and not response.getheader("Transfer-Encoding"):
            if downloaded != int(length):
                raise OSError(f"Неполный ответ: получено {downloaded} из {length} байт")

    return downloaded, perf_counter() - started


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Скорость скачивания по 10 последовательным HTTP-запросам."
    )
    parser.add_argument("url", type=http_url, help="HTTP(S)-адрес скачиваемого файла")
    args = parser.parse_args()

    total_bytes = 0
    total_seconds = 0.0
    for number in range(1, REQUEST_COUNT + 1):
        try:
            size, elapsed = download(args.url)
        except (URLError, OSError, HTTPException, ValueError) as error:
            print(f"Ошибка запроса {number}/{REQUEST_COUNT}: {error}", file=sys.stderr)
            return 1
        total_bytes += size
        total_seconds += elapsed
        print(f"Запрос {number}/{REQUEST_COUNT}: {size} байт за {elapsed:.3f} с")

    speed_mbps = total_bytes * 8 / total_seconds / 1_000_000
    print(f"\nСреднее время запроса: {total_seconds / REQUEST_COUNT:.3f} с")
    print(f"Скачано всего: {total_bytes} байт ({total_bytes / 1_000_000:.3f} MB)")
    print(f"Скорость скачивания: {speed_mbps:.3f} Мбит/с")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nИзмерение прервано.", file=sys.stderr)
        raise SystemExit(130)
