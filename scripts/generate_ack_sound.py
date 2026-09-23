"""Generate the project's original, dependency-free wake confirmation tone."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path


def main() -> None:
    sample_rate = 24_000
    duration = 0.28
    output = Path(__file__).resolve().parent.parent / "assets" / "sounds" / "wake_ack.wav"
    output.parent.mkdir(parents=True, exist_ok=True)

    samples = []
    for index in range(int(sample_rate * duration)):
        seconds = index / sample_rate
        frequency = 740 if seconds < duration / 2 else 988
        envelope = min(1.0, seconds / 0.025, (duration - seconds) / 0.045)
        amplitude = max(0.0, envelope) * 0.20
        value = int(32767 * amplitude * math.sin(2 * math.pi * frequency * seconds))
        samples.append(struct.pack("<h", value))

    with wave.open(str(output), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(b"".join(samples))
    print(output)


if __name__ == "__main__":
    main()
