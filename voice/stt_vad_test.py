import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel


ROOT = Path(__file__).resolve().parent.parent

TEMP_AUDIO = ROOT / "voice" / "stt_vad_test.wav"

SAMPLE_RATE = 16000
BLOCK_DURATION = 0.1
BLOCK_SIZE = int(SAMPLE_RATE * BLOCK_DURATION)

# 声音强度阈值
ENERGY_THRESHOLD = 0.012

# 开始说话前最多等多久
MAX_WAIT_SECONDS = 5.0

# 说话后静音多久判定结束
SILENCE_END_SECONDS = 0.6

# 防止一句话无限录
MAX_RECORD_SECONDS = 12.0


print("正在加载 Whisper small...")

model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8",
    cpu_threads=8,
)

print("模型加载完成")
print()
print("请说一句话...")
print()


frames = []

speech_started = False

start_time = time.monotonic()
last_speech_time = None


with sd.InputStream(
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="float32",
    blocksize=BLOCK_SIZE,
) as mic:

    while True:

        block, _ = mic.read(BLOCK_SIZE)

        mono = block[:, 0]

        # RMS 能量
        rms = float(
            np.sqrt(
                np.mean(
                    np.square(mono)
                )
            )
        )

        now = time.monotonic()

        # -------------------------
        # 尚未开始说话
        # -------------------------

        if not speech_started:

            if rms > ENERGY_THRESHOLD:

                speech_started = True

                last_speech_time = now

                print("检测到说话，开始录音...")

                frames.append(mono.copy())

            elif now - start_time > MAX_WAIT_SECONDS:

                print("等待超时，没有检测到说话")

                raise SystemExit

        # -------------------------
        # 已经开始说话
        # -------------------------

        else:

            frames.append(mono.copy())

            if rms > ENERGY_THRESHOLD:

                last_speech_time = now

            # 用户已经停顿
            elif (
                last_speech_time is not None
                and now - last_speech_time
                >= SILENCE_END_SECONDS
            ):

                print("检测到说话结束")

                break

            # 最长录音限制
            if now - start_time > MAX_RECORD_SECONDS:

                print("达到最长录音时间")

                break


audio = np.concatenate(frames)

audio_int16 = (
    np.clip(audio, -1.0, 1.0)
    * 32767
).astype(np.int16)


with wave.open(str(TEMP_AUDIO), "wb") as wf:

    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SAMPLE_RATE)

    wf.writeframes(
        audio_int16.tobytes()
    )


print("开始识别...")

recognize_start = time.perf_counter()

segments, info = model.transcribe(
    str(TEMP_AUDIO),

    language="zh",

    beam_size=1,

    temperature=0,

    without_timestamps=True,
)

segments = list(segments)

text = "".join(
    segment.text
    for segment in segments
).strip()


elapsed = (
    time.perf_counter()
    - recognize_start
)


print()
print("==============================")
print("识别结果：")
print(text)
print()
print(
    f"识别耗时：{elapsed:.2f} 秒"
)
print("==============================")