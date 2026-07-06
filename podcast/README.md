# Haftalik Podcast Ses Klonlama Sistemi

Newsletter icin her hafta kendi sesinizle, tamamen ucretsiz ve yerel calisan
bir podcast uretim sistemi. Internete ses/veri gondermez; her sey kendi
bilgisayarinizda calisir (Coqui XTTS-v2).

## Onemli: nerede calistirmalisiniz?

Bu betikler bir GitHub reposunda saklanir ama **kendi bilgisayarinizda**
(Mac veya Linux) calistirilmak icin tasarlanmistir. `setup.sh` calistigi
makinenin donanimini (Apple Silicon / NVIDIA GPU / CPU) otomatik algilar ve
`~/smartcity-podcast/` klasorune calisir bir kurulum yerlestirir.

## Kurulum (ilk sefer)

```bash
git clone <bu-repo>
cd smartcitybranding/podcast
bash setup.sh
```

`setup.sh` sirasiyla:
1. Donaniminizi tespit eder (Apple Silicon / NVIDIA GPU / sadece CPU).
2. Python 3.10+ ve ffmpeg'in kurulu oldugunu dogrular, eksikse kurar.
3. Donaniminiza uygun PyTorch'u kurar (MPS / CUDA / CPU).
4. Coqui XTTS-v2 (`TTS` kutuphanesi; sorun cikarsa `coqui-tts` fork'u) ve
   `pydub`'i kurar.
5. `~/smartcity-podcast/` altinda `ses_ornegim/`, `scriptler/`, `cikti/`
   klasorlerini olusturur.
6. Kisa bir test cumlesiyle sistemin calistigini dogrular.

Sadece CPU tespit edilirse betik sizi uyarir: uretim yavas olur, yaklasik
4 dakikalik bir podcast 10-20 dakika surebilir.

## Kullanim (her hafta)

1. Kendi sesinizden temiz kayit(lar) (wav/mp3/m4a) alip
   `~/smartcity-podcast/ses_ornegim/` klasorune koyun. Tek dosya yeterlidir,
   ama klasordeki **tum** dosyalar otomatik olarak birlikte kullanilir
   (XTTS-v2 birden fazla referans kaydini birlestirip daha tutarli bir
   klonlama yapar) - birkac dakikalik birden fazla kayit birakmak sonucu
   iyilestirir.
2. Haftalik podcast metnini `~/smartcity-podcast/scriptler/bu_hafta.txt`
   olarak kaydedin (format asagida).
3. Calistirin:
   ```bash
   cd ~/smartcity-podcast
   source .venv/bin/activate
   python podcast_uret.py scriptler/bu_hafta.txt
   ```
4. Sonuc: `~/smartcity-podcast/cikti/bu_hafta.mp3`

## Script dosya formati

`podcast/scriptler/ornek_bu_hafta.txt` dosyasina bakin. Ozet kurallar:

- `=====` ile cevrili bloklar (baslik, tarih, ayarlar) tamamen atlanir,
  seslendirilmez.
- `NOT:` ile baslayan satirlar (bir sonraki bos satira kadar) atlanir.
- `[PAUSE]` yazan yerde 0.7 saniyelik kisa bir duraklama olur.
- Tek basina bir satirda `---` yazan yerde 1.4 saniyelik daha uzun bir
  duraklama olur (bolum gecisi gibi dusunun).
- Geri kalan her sey metin olarak Ingilizce (`language="en"`) ve
  `ses_ornegim/` klasorundeki kaydinizla klonlanarak seslendirilir.

## Her hafta yapacaklariniz (3 madde)

1. Haftalik podcast metnini yazip `scriptler/` klasorune `.txt` olarak koyun
   (`=====` baslik blogu, gerekirse `NOT:` ve `[PAUSE]`/`---` isaretleriyle).
2. `~/smartcity-podcast` klasorunde `python podcast_uret.py scriptler/<dosya>.txt`
   komutunu calistirin.
3. `cikti/` klasorundeki MP3'u dinleyip newsletter'a ekleyin.

## Sorun giderme

- **"ses ornegini bekliyorum" uyarisi**: `ses_ornegim/` klasorune henuz bir
  ses dosyasi koymadiniz. Koydugunuzda bir sonraki calistirmada otomatik
  kullanilir.
- **Cok yavas (CPU modunda)**: Beklenen bir durum; GPU'suz sistemlerde
  normaldir. Daha kisa scriptlerle calisilabilir.
- **`TTS` kurulumu basarisiz olursa**: `setup.sh` otomatik olarak
  `coqui-tts` fork'unu dener.
- **Ilk calistirmada bir lisans onayi (y/n) sorusu cikar**: XTTS-v2 modeli
  Coqui'nin CPML lisansi ile dagitilir ve **sadece ticari olmayan
  kullanim** icin ucretsizdir. Ilk calistirmada terminalde bu sartlari
  kabul etmeniz istenir ("y" yazip Enter). Newsletter'iniz ticari bir
  urunse (reklam geliri, ucretli abonelik vb.) lisansi dikkatlice okuyun
  ve gerekirse Coqui'den ticari lisans alin (licensing@coqui.ai).

## Onemli not: model indirme

Model (~2GB) ilk calistirmada Coqui/HuggingFace sunucularindan indirilir,
bu yuzden ilk seferde internet baglantisi gereklidir ve birkac dakika
surebilir. Sonraki calistirmalarda model diskte onbelleklendigi icin
sadece uretim suresi kadar bekleyeceksiniz.
