# Haftalik Podcast Ses Klonlama Sistemi

Newsletter icin her hafta kendi sesinizle, tamamen ucretsiz ve yerel calisan
bir podcast uretim sistemi. Internete ses/veri gondermez; her sey kendi
bilgisayarinizda calisir (Coqui XTTS-v2).

## Onemli: nerede calistirmalisiniz?

Bu betikler bir GitHub reposunda saklanir ama **kendi bilgisayarinizda**
(Mac veya Linux) calistirilmak icin tasarlanmistir. `setup.sh` calistigi
makinenin donanimini (Apple Silicon / NVIDIA GPU / CPU) otomatik algilar.

**Her sey git deposunun icinde calisir** (`smartcitybranding/podcast/`) -
ayri bir kopya klasoru YOK. Yani `ses_ornegim/`, `scriptler/` ve `cikti/`
klasorleri repo ile birlikte gelir/gider; `git pull` yaptiginizda yeni
scriptler ve ses kayitlari otomatik olarak elinizde olur.

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
4. Coqui XTTS-v2'yi kurar: topluluk tarafindan surdurulen `coqui-tts`
   fork'unu (orijinal `TTS` paketinin bakimi birakildigi icin) ve
   `pydub`'i kurar.
5. `ses_ornegim/`, `scriptler/`, `cikti/` klasorlerini olusturur (bu klasor
   -- yani `smartcitybranding/podcast/` -- icinde, .venv de dahil).
6. Kisa bir test cumlesiyle sistemin calistigini dogrular.

Sadece CPU tespit edilirse betik sizi uyarir: uretim yavas olur, yaklasik
4 dakikalik bir podcast 10-20 dakika surebilir.

## Kullanim (her hafta)

1. `smartcitybranding` reposunu guncelleyin:
   ```bash
   cd ~/smartcitybranding
   git pull
   ```
2. Haftalik podcast metnini `podcast/scriptler/` klasorune `.txt` olarak
   ekleyin (repoya push edilmis olabilir, ya da kendiniz elle koyabilirsiniz).
3. Referans ses kayitlariniz zaten `podcast/ses_ornegim/` klasorundeyse ek
   bir sey yapmaniza gerek yok (yeni kayit her bolum icin GEREKLI DEGIL,
   ayni kayitlar tekrar tekrar kullanilir).
4. Calistirin:
   ```bash
   cd podcast
   source .venv/bin/activate
   python podcast_uret.py scriptler/bu_hafta.txt
   ```
5. Sonuc: `podcast/cikti/bu_hafta.mp3`

## Script dosya formati

`podcast/scriptler/ornek_bu_hafta.txt` dosyasina bakin. Ozet kurallar:

- `=====` ile cevrili bloklar (baslik, tarih, ayarlar) tamamen atlanir,
  seslendirilmez.
- `NOT:` ile baslayan satirlar (bir sonraki bos satira kadar) atlanir.
- `[PAUSE]` yazan yerde 0.7 saniyelik kisa bir duraklama olur.
- Tek basina bir satirda `---` yazan yerde 1.4 saniyelik daha uzun bir
  duraklama olur (bolum gecisi gibi dusunun).
- Bu isaretlerin kendisi (`[PAUSE]`, `---`, `=====`, `NOT: ...`) hicbir
  zaman seslendirilmez -- TTS'e sadece aralarindaki gercek konusma metni
  gonderilir.
- Geri kalan her sey metin olarak Ingilizce (`language="en"`) ve
  `ses_ornegim/` klasorundeki kaydinizla klonlanarak seslendirilir.

## Her hafta yapacaklariniz (3 madde)

1. `cd ~/smartcitybranding && git pull` ile en guncel script'i/ses
   kayitlarini alin (veya script'i kendiniz `podcast/scriptler/`'a koyun).
2. `cd podcast && source .venv/bin/activate && python podcast_uret.py scriptler/<dosya>.txt`
   komutunu calistirin.
3. `cikti/` klasorundeki MP3'u dinleyip newsletter'a ekleyin.

## Sorun giderme

- **"ses ornegini bekliyorum" uyarisi**: `ses_ornegim/` klasorune henuz bir
  ses dosyasi koymadiniz. Koydugunuzda bir sonraki calistirmada otomatik
  kullanilir.
- **"fatal: not a git repository"**: `git pull`'u `podcast/cikti/` gibi bir
  alt klasorden degil, reponun kok klasorunden (`~/smartcitybranding`)
  calistirdiginizdan emin olun.
- **`python: can't open file 'podcast_uret.py'`**: Komutu `podcast/`
  klasorunun icinden calistirdiginizdan emin olun (`cd
  ~/smartcitybranding/podcast`).
- **Cok yavas (CPU modunda)**: Beklenen bir durum; GPU'suz sistemlerde
  normaldir. Daha kisa scriptlerle calisilabilir.
- **`ImportError: cannot import name 'is_torch_greater_or_equal'` veya
  numpy 1.x/2.x uyumsuzluk uyarisi**: Orijinal `TTS` paketi kuruluysa (eski
  bir kurulumdan kalmis olabilir), guncel `numpy`/`transformers`
  surumleriyle catisiyor demektir. Duzeltme:
  ```bash
  pip uninstall -y TTS
  pip install coqui-tts
  ```
  (`coqui-tts` ayni `TTS` Python modulunu sagladigi icin kod degismeden
  calisir.) `setup.sh` yeni kurulumlarda zaten dogrudan `coqui-tts` kurar.
- **`ImportError: ... requires the PyTorch and Torchaudio libraries`** veya
  **`Disabling PyTorch because PyTorch >= 2.4 is required but found ...`**:
  `torch` ve/veya `torchaudio` eksik ya da eski. Duzeltme:
  ```bash
  pip install --upgrade torch torchaudio
  ```
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
