# Bremen Şehir Nabzı

Bremen için hava kalitesi (AQICN) ve trafik (TomTom) verilerini çeken,
ardından Anthropic Claude API'sini kullanarak bu veriden günlük bir
Türkçe "şehir nabzı" özeti üreten script.

## Kurulum

```bash
pip install -r requirements.txt
cp .env.example .env
# .env dosyasını kendi API anahtarlarınızla doldurun
```

Gereken API anahtarları:

- `AQICN_API_TOKEN` — [aqicn.org/data-platform/token](https://aqicn.org/data-platform/token/)
- `TOMTOM_API_KEY` — [developer.tomtom.com](https://developer.tomtom.com/)
- `ANTHROPIC_API_KEY` — [console.anthropic.com](https://console.anthropic.com/)

## Kullanım

```bash
python bremen_city_pulse.py
```

Script sırasıyla:

1. AQICN'den Bremen için hava kalitesi verisini (AQI, PM2.5, PM10, NO2, O3 vb.) çeker.
2. TomTom Traffic Flow API'sinden şehir merkezi için anlık trafik akış verisini çeker.
3. Bu verileri Claude'a (`claude-opus-4-8`) göndererek 3-4 paragraflık günlük bir
   şehir nabzı özeti oluşturur ve konsola yazdırır.
