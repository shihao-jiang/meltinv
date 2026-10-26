# Docker image of the meltinv web app, for hosts that run containers: a Hugging
# Face Docker Space (which needs a paid plan since July 2026) or your own server.
# The free option is Streamlit Community Cloud; see ../README.md.
# For a Space, copy this file and README.md (same folder) into it. The build
# downloads meltinv and the app from GitHub, so pushing to GitHub and then
# choosing "Factory rebuild" in the Space settings updates the website.
FROM python:3.11-slim

# git is needed to install meltPT from GitHub
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Branch or tag of meltinv to publish, e.g. main or v0.1.0
ARG MELTINV_REF=main
RUN git clone --depth 1 --branch ${MELTINV_REF} https://github.com/shihao-jiang/meltinv.git /opt/meltinv \
    && pip install --no-cache-dir "/opt/meltinv[app]"

# Hugging Face runs Spaces as user 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user MPLBACKEND=Agg
WORKDIR /opt/meltinv/app

EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
# XSRF protection blocks file uploads inside the Hugging Face page frame
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.enableXsrfProtection=false"]
