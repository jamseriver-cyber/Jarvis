import time
from pathlib import Path

import sounddevice as sd
import sherpa_onnx

from PySide6.QtCore import QThread, Signal


class WakeListener(QThread):

    wake_detected = Signal(str)


    def __init__(self,parent=None):

        super().__init__(parent)

        self.root = Path(__file__).resolve().parent.parent


        self.model_dir = (
            self.root
            /
            "models"
            /
            "kws"
            /
            "sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20"
        )


        self.keywords_file = (
            self.root
            /
            "models"
            /
            "kws"
            /
            "keywords.txt"
        )


        self.enabled = True

        self.stream = None

        self.spotter = None



    def pause(self):

        print("[Wake] pause")

        self.enabled=False



    def resume(self):

        print("[Wake] resume")

        self.enabled=True


        if self.stream:

            try:
                self.spotter.reset_stream(
                    self.stream
                )

            except:
                pass



    def run(self):

        print("[Wake] 正在加载唤醒模型...")


        try:


            self.spotter = sherpa_onnx.KeywordSpotter(

                tokens=str(
                    self.model_dir/
                    "tokens.txt"
                ),


                encoder=str(
                    self.model_dir/
                    "encoder-epoch-13-avg-2-chunk-8-left-64.int8.onnx"
                ),


                decoder=str(
                    self.model_dir/
                    "decoder-epoch-13-avg-2-chunk-8-left-64.onnx"
                ),


                joiner=str(
                    self.model_dir/
                    "joiner-epoch-13-avg-2-chunk-8-left-64.int8.onnx"
                ),


                keywords_file=str(
                    self.keywords_file
                ),


                num_threads=2,

                provider="cpu",

                keywords_score=1.5,

                keywords_threshold=0.18

            )


            self.stream = (
                self.spotter.create_stream()
            )


            sample_rate=16000


            block_size=1600


            last_time=0



            print(
                "[Wake] 等待：贾维斯"
            )



            with sd.InputStream(

                samplerate=sample_rate,

                channels=1,

                dtype="float32",

                blocksize=block_size


            ) as mic:


                while not self.isInterruptionRequested():


                    if not self.enabled:

                        time.sleep(0.05)

                        continue



                    samples,_=mic.read(
                        block_size
                    )


                    samples=samples.reshape(-1)


                    self.stream.accept_waveform(
                        sample_rate,
                        samples
                    )



                    while self.spotter.is_ready(
                        self.stream
                    ):


                        self.spotter.decode_stream(
                            self.stream
                        )


                        result=(
                            self.spotter.get_result(
                                self.stream
                            )
                        )



                        if result:


                            now=time.monotonic()


                            if now-last_time>2:


                                last_time=now


                                print(
                                    "[Wake] WAKE:",
                                    result
                                )


                                self.wake_detected.emit(
                                    result
                                )


                                self.spotter.reset_stream(
                                    self.stream
                                )



        except Exception as e:


            print(
                "[Wake ERROR]",
                e
            )


        finally:

            print(
                "[Wake] stopped"
            )