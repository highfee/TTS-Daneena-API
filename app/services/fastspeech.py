

import nltk
import torch
from espnet2.bin.tts_inference import Text2Speech
from espnet.nets.pytorch_backend.nets_utils import make_pad_mask

from app.services.prosody import get_prosody

try:
    nltk.data.find('taggers/averaged_perceptron_tagger_eng')
except LookupError:
    nltk.download('averaged_perceptron_tagger_eng')


class FastSpeech2Service:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FastSpeech2Service, cls).__new__(cls)
            cls._instance.tts = Text2Speech.from_pretrained(
                model_tag="espnet/kan-bayashi_ljspeech_fastspeech2",
                device="cpu"
            )
        return cls._instance

    def synthesize(self, text: str, prosody: dict):
        with torch.no_grad():
            # 1. Preprocess text to tensor
            text_tensor = self.tts.preprocess_fn("<dummy>", dict(text=text))["text"]
            if not isinstance(text_tensor, torch.Tensor):
                text_tensor = torch.tensor(text_tensor, dtype=torch.long)
            
            fs2 = self.tts.tts # The actual FastSpeech2 model instance
            
            # --- ADD EOS Padding as expected by FastSpeech2 ---
            text_tensor = torch.nn.functional.pad(text_tensor, [0, 1], "constant", fs2.eos)
            # --------------------------------------------------
            
            text_tensor = text_tensor.unsqueeze(0)
            text_lengths = torch.tensor([text_tensor.shape[1]], dtype=torch.long)
            
            # Send to model device
            text_tensor = text_tensor.to(self.tts.device)
            text_lengths = text_lengths.to(self.tts.device)
            
            # 2. Extract Encoder hidden states
            x_masks = fs2._source_mask(text_lengths)
            hs, _ = fs2.encoder(text_tensor, x_masks)

            # 3. Predict Variance (Pitch, Energy, Duration)
            d_masks = make_pad_mask(text_lengths).to(text_tensor.device)
            p_outs = fs2.pitch_predictor(hs, d_masks.unsqueeze(-1))
            e_outs = fs2.energy_predictor(hs, d_masks.unsqueeze(-1))
            d_outs = fs2.duration_predictor.inference(hs, d_masks)

            # --- APPLY EMOTION-BASED SHIFTS ---
            pitch_shift = prosody.get("pitch_shift", 0.0)
            if pitch_shift != 0.0:
                p_outs = p_outs + pitch_shift
                
            energy_shift = prosody.get("energy_shift", 0.0)
            if energy_shift != 0.0:
                e_outs = e_outs + energy_shift
            # ----------------------------------
            
            # Add Embeddings
            p_embs = fs2.pitch_embed(p_outs.transpose(1, 2)).transpose(1, 2)
            e_embs = fs2.energy_embed(e_outs.transpose(1, 2)).transpose(1, 2)
            hs = hs + e_embs + p_embs
            
            # 4. Length regulation using the speed control alpha
            alpha = prosody.get("speed", 1.0)
            hs = fs2.length_regulator(hs, d_outs, alpha)
            
            # 5. Decode
            zs, _ = fs2.decoder(hs, None)
            before_outs = fs2.feat_out(zs).view(zs.size(0), -1, fs2.odim)
            
            if fs2.postnet is None:
                feat_gen = before_outs
            else:
                feat_gen = before_outs + fs2.postnet(before_outs.transpose(1, 2)).transpose(1, 2)
            
            # --- DENORMALIZE (Critical for Vocoder quality) ---
            if self.tts.model.normalize is not None:
                # normalize.inverse returns (denorm_feats, lengths)
                # denorm_feats is (Batch, Time, Feat)
                feat_gen = self.tts.model.normalize.inverse(feat_gen.clone())[0][0]
            else:
                feat_gen = feat_gen[0]
            # ---------------------------------------------------

            return feat_gen
