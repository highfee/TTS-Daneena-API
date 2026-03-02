

import torch
from espnet2.bin.tts_inference import Text2Speech

class HiFiGANService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HiFiGANService, cls).__new__(cls)
            cls._instance.tts = Text2Speech.from_pretrained(
                model_tag="espnet/kan-bayashi_ljspeech_fastspeech2",
                device="cpu"
            )
        return cls._instance

    def vocode(self, mel):
        with torch.no_grad():
            # Ensure mel is on the same device as the vocoder
            mel = mel.to(self.tts.device)
            # Invoke the vocoder callable
            if self.tts.vocoder is not None:
                wav = self.tts.vocoder(mel)
            else:
                raise RuntimeError("No vocoder found in the Text2Speech instance.")
                
        return wav.cpu().numpy()
