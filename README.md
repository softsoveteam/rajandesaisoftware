# Simple Signage Player V2

Clean and simple signage player that:
1. Checks API for schedules
2. Downloads videos for all schedules
3. Plays video based on current time matching schedule_time
4. Automatically switches videos when schedule time arrives

## Setup

1. Copy `config.json.example` to `config.json`
2. Fill in your API details:
   - `server_url`: Your API server URL
   - `screen_id`: Your screen ID
   - `api_key`: Your screen API key
   - `video_dir`: Where to store videos (e.g., `C:\signage\videos`)
   - `vlc_path`: Path to VLC executable

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run:
```bash
python player.py
```

## How It Works

1. **Checks schedules** from API every minute
2. **Downloads videos** for all schedules (reuses if already downloaded)
3. **Plays video** based on current time - finds schedule that should be playing now
4. **Switches automatically** when schedule time arrives
5. **Restarts VLC** if it crashes

## Simple Workflow

- No complex logic
- No version tracking files
- Just: Get schedules → Download videos → Play at scheduled time
- That's it!

