"""Microphone capture, endpoint detection, and local Whisper transcription."""

from __future__ import annotations

import threading
import time
import wave
from collections import deque
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from PySide6.QtCore import QThread, Signal
from runtime_paths import user_root


class SttListener(QThread):
    listening_started = Signal()
    transcribing_started = Signal()
    audio_level = Signal(float)
    text_ready = Signal(str)
    no_speech = Signal()
    error_occurred = Signal(str)

    _model = None
    _model_lock = threading.Lock()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.root = user_root()
        self.temp_audio = self.root / "voice" / "current_input.wav"
        self.sample_rate = 16000
        self.block_duration = 0.1
        self.block_size = int(self.sample_rate * self.block_duration)
        self.energy_threshold = 0.012
        self.max_wait_seconds = 7.0
        self.silence_end_seconds = 0.75
        self.max_record_seconds = 18.0

    @classmethod
    def _whisper_model(cls):
        with cls._model_lock:
            if cls._model is None:
                print("[STT] 首次加载 Whisper small...")
                cls._model = WhisperModel(
                    "small",
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=8,
                )
                print("[STT] Whisper 模型准备完成")
        return cls._model

    def run(self):
        try:
            model = self._whisper_model()
            self.listening_started.emit()

            frames = []
            pre_roll = deque(maxlen=4)
            speech_started = False
            capture_started = time.monotonic()
            last_speech_time = None
            block_index = 0

            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=self.block_size,
            ) as mic:
                while not self.isInterruptionRequested():
                    block, overflowed = mic.read(self.block_size)
                    if overflowed:
                        print("[STT] 麦克风缓冲区发生溢出")

                    mono = block[:, 0]
                    rms = float(np.sqrt(np.mean(np.square(mono))))
                    now = time.monotonic()
                    block_index += 1

                    if block_index % 2 == 0:
                        self.audio_level.emit(min(1.0, rms / 0.08))

                    if not speech_started:
                        pre_roll.append(mono.copy())
                        if rms > self.energy_threshold:
                            speech_started = True
                            last_speech_time = now
                            frames.extend(pre_roll)
                            print("[STT] 检测到用户说话")
                        elif now - capture_started > self.max_wait_seconds:
                            print("[STT] 等待用户说话超时")
                            self.no_speech.emit()
                            return
                    else:
                        frames.append(mono.copy())
                        if rms > self.energy_threshold:
                            last_speech_time = now
                        elif (
                            last_speech_time is not None
                            and now - last_speech_time >= self.silence_end_seconds
                        ):
                            print("[STT] 检测到说话结束")
                            break

                        if now - capture_started > self.max_record_seconds:
                            break

            self.audio_level.emit(0.0)
            if self.isInterruptionRequested():
                return
            if not frames:
                self.no_speech.emit()
                return

            audio = np.concatenate(frames)
            audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)

            self.temp_audio.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(self.temp_audio), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_int16.tobytes())

            self.transcribing_started.emit()
            print("[STT] 开始识别...")
            start = time.perf_counter()
            segments, _ = model.transcribe(
                str(self.temp_audio),
                language="zh",
                beam_size=1,
                temperature=0,
                vad_filter=True,
                without_timestamps=True,
                condition_on_previous_text=False,
            )
            text = "".join(segment.text for segment in segments).strip()
            elapsed = time.perf_counter() - start
            print(f"[STT] 识别结果：{text}")
            print(f"[STT] 识别耗时：{elapsed:.2f} 秒")
            self.text_ready.emit(text)

        except Exception as exc:
            print(f"[STT] ERROR: {exc}")
            self.audio_level.emit(0.0)
            self.error_occurred.emit(str(exc))
