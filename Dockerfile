FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=3000
WORKDIR /app

# One copy from the ZIP root: Python modules, frontend and world_data together.
COPY . /app/

# Explicit validation BEFORE downloading dependencies.
RUN python -c "from pathlib import Path; required=['requirements.txt','main.py','server.py','bot.py','game.py','engine.py','world.py','offline_catalog.py','verified_rosters.py','static/index.html','static/app.js','static/style.css','world_data/league_registry.json','world_data/premier_league_2026_27_first_team.txt','world_data/featured_2026_27_first_team.txt']; missing=[p for p in required if not Path(p).is_file()]; missing += ['world_data/packs/*.json'] if not list(Path('world_data/packs').glob('*.json')) else []; assert not missing, 'VELTON: files missing from Docker build context (unpack ZIP into hosting project ROOT): '+', '.join(missing)"
RUN python -m pip install --no-cache-dir -r /app/requirements.txt
RUN python -m compileall -q /app/main.py /app/server.py /app/bot.py /app/game.py /app/engine.py /app/world.py /app/offline_catalog.py /app/verified_rosters.py && mkdir -p /app/data

EXPOSE 3000
CMD ["python", "-u", "main.py"]
