#!/usr/bin/env python3
"""Haftalik podcast ses uretim betigi.

Kullanim:
    python podcast_uret.py scriptler/bu_hafta.txt

Script dosyasi format kurallari:
  - ===== ile cevrili bloklar (baslik/ayar) tamamen atlanir.
  - "NOT:" ile baslayan satirlar (bir sonraki bos satira kadar) atlanir.
  - "[PAUSE]" isareti 0.7 saniyelik sessizlige donusur.
  - Tek basina bir satirda olan "---" 1.4 saniyelik sessizlige donusur.
  - Geri kalan her metin parcasi XTTS-v2 ile Ingilizce (language="en"),
    ses_ornegim/ klasorundeki referans kayitla klonlanarak seslendirilir.
"""

import re
import sys
from pathlib import Path

PAUSE_SILENCE_MS = 700
SECTION_SILENCE_MS = 1400
MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"

BASE_DIR = Path(__file__).resolve().parent
SES_ORNEGIM_DIR = BASE_DIR / "ses_ornegim"
CIKTI_DIR = BASE_DIR / "cikti"

# .m4a intentionally excluded: it needs an ffmpeg backend to decode via
# torchaudio/soundfile, while these formats load directly.
REFERENCE_EXTENSIONS = (".wav", ".mp3", ".flac", ".ogg")


def temizle_ve_ayikla(ham_metin: str) -> str:
    """===== bloklarini ve NOT: bolumlerini cikarip sadece konusma metnini dondurur."""
    # ===== ... ===== bloklarini (baslik/ayar) tamamen sil.
    metin = re.sub(r"^[ \t]*=+[ \t]*\n.*?\n[ \t]*=+[ \t]*\n?", "", ham_metin, flags=re.DOTALL | re.MULTILINE)

    # "NOT:" ile baslayan paragraflari (bir sonraki bos satira kadar) sil.
    satirlar = metin.split("\n")
    temiz_satirlar = []
    not_blogu_icinde = False
    for satir in satirlar:
        if satir.strip().upper().startswith("NOT:"):
            not_blogu_icinde = True
            continue
        if not_blogu_icinde:
            if satir.strip() == "":
                not_blogu_icinde = False
            else:
                continue
        temiz_satirlar.append(satir)

    return "\n".join(temiz_satirlar).strip()


def parcalara_ayir(konusma_metni: str):
    """Metni --- (bolum) ve [PAUSE] (kisa duraklama) isaretlerine gore parcalara ayirir.

    Donen deger: liste halinde ogeler.
      ("metin", "...") -> seslendirilecek metin parcasi
      ("sessizlik", ms) -> araya eklenecek sessizlik
    """
    ogeler = []
    bolumler = re.split(r"^[ \t]*-{3,}[ \t]*$", konusma_metni, flags=re.MULTILINE)

    for i, bolum in enumerate(bolumler):
        if i > 0:
            ogeler.append(("sessizlik", SECTION_SILENCE_MS))

        pause_parcalari = re.split(r"\[PAUSE\]", bolum)
        for j, parca in enumerate(pause_parcalari):
            if j > 0:
                ogeler.append(("sessizlik", PAUSE_SILENCE_MS))
            metin = " ".join(parca.split())
            if metin:
                ogeler.append(("metin", metin))

    return ogeler


def referans_sesleri_bul():
    """ses_ornegim/ klasorundeki tum referans ses dosyalarini dondurur.

    XTTS-v2 birden fazla referans kaydini ayni anda kabul eder (speaker_wav
    bir liste olabilir) ve bu, klonlama kalitesini artirir. Bu yuzden tek
    dosya yerine klasordeki tum uygun dosyalar kullanilir.
    """
    if not SES_ORNEGIM_DIR.exists():
        return []
    return [
        dosya for dosya in sorted(SES_ORNEGIM_DIR.iterdir())
        if dosya.suffix.lower() in REFERENCE_EXTENSIONS
    ]


def cihaz_sec():
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def main():
    if len(sys.argv) != 2:
        print("Kullanim: python podcast_uret.py scriptler/bu_hafta.txt")
        sys.exit(1)

    script_yolu = Path(sys.argv[1])
    if not script_yolu.exists():
        print(f"HATA: '{script_yolu}' bulunamadi.")
        sys.exit(1)

    CIKTI_DIR.mkdir(parents=True, exist_ok=True)

    ham_metin = script_yolu.read_text(encoding="utf-8")
    konusma_metni = temizle_ve_ayikla(ham_metin)
    ogeler = parcalara_ayir(konusma_metni)

    metin_parca_sayisi = sum(1 for tur, _ in ogeler if tur == "metin")
    if metin_parca_sayisi == 0:
        print("HATA: Script icinde seslendirilecek metin bulunamadi. Dosyayi kontrol edin.")
        sys.exit(1)

    print(f"Script okundu: {script_yolu.name}")
    print(f"Toplam {metin_parca_sayisi} konusma parcasi seslendirilecek.\n")

    referans_sesler = referans_sesleri_bul()
    if not referans_sesler:
        print("UYARI: ses_ornegim/ klasorunde referans ses kaydi bulunamadi.")
        print("Modelin varsayilan sesiyle devam ediliyor. Ses ornegini bekliyorum.\n")
    else:
        isimler = ", ".join(dosya.name for dosya in referans_sesler)
        print(f"Referans ses kayitlari kullaniliyor ({len(referans_sesler)} dosya): {isimler}\n")

    print("Model yukleniyor (Coqui XTTS-v2)... ilk calistirmada model indirilecegi icin biraz surebilir.")
    from TTS.api import TTS
    from pydub import AudioSegment

    cihaz = cihaz_sec()
    print(f"Kullanilan islemci: {cihaz}")
    if cihaz == "cpu":
        print("UYARI: GPU/MPS bulunamadi, uretim CPU'da yapiliyor (daha yavas olabilir).\n")

    tts = TTS(MODEL_NAME).to(cihaz)

    import tempfile

    parcalar_audio = []
    islenen_parca = 0

    with tempfile.TemporaryDirectory() as gecici_klasor:
        for tur, deger in ogeler:
            if tur == "sessizlik":
                parcalar_audio.append(AudioSegment.silent(duration=deger))
                continue

            islenen_parca += 1
            print(f"[{islenen_parca}/{metin_parca_sayisi}] seslendiriliyor: \"{deger[:60]}{'...' if len(deger) > 60 else ''}\"")

            gecici_wav = str(Path(gecici_klasor) / f"parca_{islenen_parca}.wav")

            if referans_sesler:
                tts.tts_to_file(
                    text=deger,
                    speaker_wav=[str(dosya) for dosya in referans_sesler],
                    language="en",
                    file_path=gecici_wav,
                )
            else:
                varsayilan_konusmaci = tts.speakers[0] if getattr(tts, "speakers", None) else None
                tts.tts_to_file(
                    text=deger,
                    speaker=varsayilan_konusmaci,
                    language="en",
                    file_path=gecici_wav,
                )

            parcalar_audio.append(AudioSegment.from_wav(gecici_wav))

    print("\nTum parcalar birlestiriliyor...")
    birlesik_ses = AudioSegment.empty()
    for parca in parcalar_audio:
        birlesik_ses += parca

    cikti_yolu = CIKTI_DIR / f"{script_yolu.stem}.mp3"
    birlesik_ses.export(cikti_yolu, format="mp3", bitrate="192k")

    print(f"\nTamamlandi! Podcast kaydedildi: {cikti_yolu}")


if __name__ == "__main__":
    main()
