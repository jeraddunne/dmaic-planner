# DMAIC Planner web app (ARI 410/510 Phase 3). Same image locally and on Cloud Run.
#
#   docker build -t dmaic-planner .
#   docker run --rm -p 7860:7860 dmaic-planner        # then open http://localhost:7860
#
# Cloud Run builds this file itself (gcloud run deploy --source .); see deploy/README.md.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/hf \
    GRADIO_ANALYTICS_ENABLED=False \
    PORT=7860

RUN useradd --create-home --uid 10001 app
WORKDIR /srv

# CPU-only torch from PyTorch's CPU index first. The default Linux wheel pulls in
# several GB of CUDA libraries that a CPU host never uses; installing it first means
# app/requirements.txt finds torch==2.15.0 already satisfied.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.15.0
COPY app/requirements.txt app/requirements.txt
RUN pip install -r app/requirements.txt

# Bake the sentence encoder into the image so a cold start never downloads it: the
# exact id and revision the deployed model names in model.json ("base_model").
# Loading it through sentence-transformers fetches only the files the app loads
# (about 90 MB), not the whole Hugging Face repo.
COPY models/phase3/c2/model.json models/phase3/c2/model.json
RUN python -c "import json; from sentence_transformers import SentenceTransformer as S; \
b = json.load(open('models/phase3/c2/model.json', encoding='utf-8'))['base_model']; \
S(b['id'], revision=b['revision'], device='cpu'); print('baked', b['id'], b['revision'])" \
 && chown -R app:app "$HF_HOME"
# Never reach for the network at startup: a missing file fails fast instead of
# downloading during someone's demo. Anything else the chosen model needs from
# Hugging Face must be fetched in a RUN step above, like the encoder.
ENV HF_HUB_OFFLINE=1

# Only what the app runs (.dockerignore is an allowlist). The model's weights
# (model.json) were copied above.
COPY src/ src/
COPY rules/ rules/
COPY app/ app/

USER app
EXPOSE 7860
CMD ["python", "-m", "app.main"]
