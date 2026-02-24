FROM python:3.12-slim

WORKDIR /app

# Copy source and project metadata
COPY pyproject.toml .
COPY src/ src/

# Install the package
RUN pip install --no-cache-dir .

# SCIM configuration
# Preset: permissive (default), pingdirectory, put_only
ENV SCIM_PRESET=permissive
# Granular overrides (uncomment to override preset):
# ENV SCIM_GROUPS_PUT=true
# ENV SCIM_GROUPS_PATCH=true

EXPOSE 8000

CMD ["uvicorn", "scim_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
