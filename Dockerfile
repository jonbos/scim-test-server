FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn pydantic

COPY main.py storage.py models.py config.py ./

# SCIM configuration
# Preset: permissive (default), pingdirectory, put_only
ENV SCIM_PRESET=permissive
# Granular overrides (uncomment to override preset):
# ENV SCIM_GROUPS_PUT=true
# ENV SCIM_GROUPS_PATCH=true

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
