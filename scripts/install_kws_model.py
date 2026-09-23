"""Download the wake-word model directly from the sherpa-onnx release."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path


MODEL_NAME = "sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20"
MODEL_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/"
    f"{MODEL_NAME}.tar.bz2"
)
ARCHIVE_SHA256 = "68447f4fbc67e70eee3a93961f36e81e98f47aef73ce7e7ca00885c6cd3616a6"
REQUIRED_FILES = (
    "tokens.txt",
    "encoder-epoch-13-avg-2-chunk-8-left-64.int8.onnx",
    "decoder-epoch-13-avg-2-chunk-8-left-64.onnx",
    "joiner-epoch-13-avg-2-chunk-8-left-64.int8.onnx",
)


def verify_archive(path: Path) -> None:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != ARCHIVE_SHA256:
        raise ValueError("唤醒模型文件的 SHA-256 校验失败，已拒绝解压。")


def install_from_archive(archive: Path, destination: Path) -> None:
    verify_archive(archive)
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, mode="r:bz2") as package:
        for name in REQUIRED_FILES:
            member = package.getmember(f"{MODEL_NAME}/{name}")
            if not member.isfile():
                raise ValueError(f"模型归档中的 {name} 不是普通文件。")
            source = package.extractfile(member)
            if source is None:
                raise ValueError(f"模型归档缺少 {name}。")
            with source, (destination / name).open("wb") as target:
                shutil.copyfileobj(source, target)


def main() -> None:
    parser = argparse.ArgumentParser(description="Install the local Jarvis wake model")
    parser.add_argument("--archive", type=Path, help="Use an already downloaded archive")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    destination = root / "models" / "kws" / MODEL_NAME
    if all((destination / name).is_file() for name in REQUIRED_FILES):
        print("[Jarvis] 唤醒模型已经存在，无需重新下载。")
        return

    if args.archive:
        install_from_archive(args.archive, destination)
    else:
        with tempfile.TemporaryDirectory(prefix="jarvis-kws-") as temporary:
            archive = Path(temporary) / f"{MODEL_NAME}.tar.bz2"
            print(f"[Jarvis] 从上游下载唤醒模型：{MODEL_URL}")
            with urllib.request.urlopen(MODEL_URL, timeout=120) as response:
                with archive.open("wb") as target:
                    shutil.copyfileobj(response, target)
            install_from_archive(archive, destination)

    print(f"[Jarvis] 唤醒模型已安装：{destination}")


if __name__ == "__main__":
    main()
