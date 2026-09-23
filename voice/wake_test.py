from pathlib import Path

import sounddevice as sd
import sherpa_onnx


ROOT = Path(__file__).resolve().parent.parent

MODEL_DIR = (
    ROOT
    / "models"
    / "kws"
    / "sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20"
)

KEYWORDS_FILE = (
    ROOT
    / "models"
    / "kws"
    / "keywords.txt"
)


print("正在加载贾维斯唤醒模型...")


spotter = sherpa_onnx.KeywordSpotter(
    tokens=str(MODEL_DIR / "tokens.txt"),

    encoder=str(
        MODEL_DIR
        / "encoder-epoch-13-avg-2-chunk-8-left-64.int8.onnx"
    ),

    decoder=str(
        MODEL_DIR
        / "decoder-epoch-13-avg-2-chunk-8-left-64.onnx"
    ),

    joiner=str(
        MODEL_DIR
        / "joiner-epoch-13-avg-2-chunk-8-left-64.int8.onnx"
    ),

    keywords_file=str(KEYWORDS_FILE),

    num_threads=2,

    provider="cpu",

    keywords_score=1.5,
    keywords_threshold=0.18,
)


stream = spotter.create_stream()

sample_rate = 16000
block_size = int(sample_rate * 0.1)


print()
print("==============================")
print(" Personal Jarvis Wake Test")
print("==============================")
print()
print("请对着麦克风说：贾维斯")
print("按 Ctrl+C 退出")
print()


try:
    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        blocksize=block_size,
    ) as mic:

        while True:

            samples, _ = mic.read(block_size)

            samples = samples.reshape(-1)

            stream.accept_waveform(
                sample_rate,
                samples
            )

            while spotter.is_ready(stream):

                spotter.decode_stream(stream)

                result = spotter.get_result(stream)

                if result:
                    print()
                    print("==============================")
                    print(" WAKE DETECTED")
                    print(f" Keyword: {result}")
                    print("==============================")
                    print()

                    spotter.reset_stream(stream)

except KeyboardInterrupt:
    print("\n测试结束")