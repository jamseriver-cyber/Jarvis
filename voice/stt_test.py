import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel


ROOT = Path(__file__).resolve().parent.parent
TEMP_AUDIO = ROOT / "voice" / "stt_test.wav"

SAMPLE_RATE = 16000
RECORD_SECONDS = 5


print("正在加载 Whisper small...")

model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8",
    cpu_threads=8,
)

print("模型加载完成。")
print()
print("准备录音 5 秒。")
print("现在开始说一句中文……")


audio = sd.rec(
    int(RECORD_SECONDS * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="float32",
)

sd.wait()

print("录音结束，开始识别...")


audio_int16 = (
    np.clip(audio[:, 0], -1.0, 1.0) * 32767
).astype(np.int16)


with wave.open(str(TEMP_AUDIO), "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(audio_int16.tobytes())


start = time.perf_counter()

segments, info = model.transcribe(
    str(TEMP_AUDIO),

    language="zh",

    beam_size=1,

    temperature=0,

    without_timestamps=True,
)


segments = list(segments)

elapsed = time.perf_counter() - start

text = "".join(
    segment.text
    for segment in segments
).strip()


print()
print("==============================")
print("识别结果：")
print(text)
print()
print(f"识别耗时：{elapsed:.2f} 秒")
print("==============================")