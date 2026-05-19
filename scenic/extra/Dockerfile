# Gebruik een officiële Python runtime
FROM python:3.9-slim

# Maak een nieuwe gebruiker aan (verplicht voor Hugging Face)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Stel de werkmap in
WORKDIR $HOME/app

# Kopieer requirements en installeer ze
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Kopieer de rest van de code
COPY --chown=user . .

# Start FastAPI op poort 7860
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860"]
