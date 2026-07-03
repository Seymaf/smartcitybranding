# Bremen City Pulse

A small pipeline that fetches live air quality and traffic data for Bremen,
Germany, and turns it into a short, warm daily "City Pulse" summary using the
Anthropic Claude API — useful as a tourism/branding-style daily briefing.

## How it works

1. **Air quality** — [`air_quality.py`](air_quality.py) fetches Bremen's
   current air quality index and pollutant levels from the
   [OpenWeatherMap Air Pollution API](https://openweathermap.org/api/air-pollution)
   (free tier).
2. **Traffic** — [`traffic.py`](traffic.py) fetches current vs. free-flow
   traffic speed for Bremen's city center from the
   [TomTom Traffic Flow API](https://developer.tomtom.com/traffic-api/documentation/traffic-flow/flow-segment-data)
   (free tier).
3. **Summary** — [`city_pulse.py`](city_pulse.py) sends both datasets to the
   Anthropic Claude API (`claude-opus-4-8`), which writes a short, warm,
   tourism/branding-toned but factually grounded daily summary.
4. **Pipeline** — [`main.py`](main.py) runs the three steps in order and
   prints the result.

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Create your `.env` file from the template:

   ```bash
   cp .env.example .env
   ```

3. Fill in `.env` with your API keys (see below).

## Required API keys

| Variable               | Where to get it                                                                 | Notes                          |
| ----------------------- | -------------------------------------------------------------------------------- | ------------------------------- |
| `OPENWEATHER_API_KEY`   | [openweathermap.org/api](https://openweathermap.org/api)                        | Free tier covers the Air Pollution API |
| `TOMTOM_API_KEY`        | [developer.tomtom.com](https://developer.tomtom.com/)                           | Free tier covers Traffic Flow API |
| `ANTHROPIC_API_KEY`     | [console.anthropic.com](https://console.anthropic.com/)                         | Used to generate the summary text |

None of these keys are checked into the repo — `.env` is git-ignored, and
`.env.example` only holds placeholder values.

## Running

```bash
python main.py
```

This prints progress as it fetches each data source, then prints the
generated "City Pulse" summary for Bremen.

## Project structure

```
config.py        # env var loading + shared constants (Bremen coordinates, timeouts)
air_quality.py    # OpenWeatherMap Air Pollution API client
traffic.py        # TomTom Traffic Flow API client
city_pulse.py     # builds the prompt and calls Claude to generate the summary
main.py           # orchestrates the pipeline end-to-end
```
