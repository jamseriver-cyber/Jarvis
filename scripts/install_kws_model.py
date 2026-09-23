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
FILE_SHA256 = {
    "tokens.txt": "2d3f32311f9b692b964da3c90e830258d3e78e013cb0c992dbfb15cd5a1a71b0",
    "encoder-epoch-13-avg-2-chunk-8-left-64.int8.onnx": "2ca84d6bfe73e1ea3c9c49f600f7cad1c9ddd423c53c906b8bfe802444dd78d5",
    "decoder-epoch-13-avg-2-chunk-8-left-64.onnx": "63a22dd60f40fff082ac3e09afa507f6787da36df76ded2fbe145fa233e22c21",
    "joiner-epoch-13-avg-2-chunk-8-left-64.int8.onnx": "190d4067b4cc20b72a42a1916e69d92052000fb7051a427ebb1bc72a69207dc1",
}


def verify_archive(path: Path) -> None:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != ARCHIVE_SHA256:
        raise ValueError("唤醒模型文件的 SHA-256 校验失败，已拒绝解压。")


def verify_model_files(folder: Path) -> None:
    for name, expected in FILE_SHA256.items():
        path = Path(folder) / name
        if not path.is_file():
            raise ValueError(f"唤醒模型缺少 {name}。")
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected:
            raise ValueError(f"唤醒模型 {name} 校验失败，未导入。")


def import_model_folder(folder: Path, destination: Path) -> None:
    folder = Path(folder)
    destination = Path(destination)
    verify_model_files(folder)
    destination.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_FILES:
        shutil.copy2(folder / name, destination / name)


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
    verify_model_files(destination)


def install_model(destination: Path, archive: Path | None = None) -> None:
    destination = Path(destination)
    if all((destination / name).is_file() for name in REQUIRED_FILES):
        print("[Jarvis] 唤醒模型已经存在，无需重新下载。")
        return

    if archive:
        install_from_archive(archive, destination)
    else:
        with tempfile.TemporaryDirectory(prefix="jarvis-kws-") as temporary:
            downloaded = Path(temporary) / f"{MODEL_NAME}.tar.bz2"
            print(f"[Jarvis] 从上游下载唤醒模型：{MODEL_URL}")
            with urllib.request.urlopen(MODEL_URL, timeout=120) as response:
                with downloaded.open("wb") as target:
                    shutil.copyfileobj(response, target)
            install_from_archive(downloaded, destination)

    print(f"[Jarvis] 唤醒模型已安装：{destination}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Install the local Jarvis wake model")
    parser.add_argument("--archive", type=Path, help="Use an already downloaded archive")
    parser.add_argument("--destination", type=Path, help="Install into a writable model folder")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    destination = args.destination or root / "models" / "kws" / MODEL_NAME
    install_model(destination, args.archive)


if __name__ == "__main__":
    main()
