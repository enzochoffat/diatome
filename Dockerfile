# syntax=docker/dockerfile:1
FROM python:3.12-slim

# System dependencies for geopandas/shapely/pyogrio + PyQt6 headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev \
    libproj-dev proj-data \
    libgeos-dev \
    libspatialindex-dev \
    gettext \
    tk \
    libgl1 libegl1 libxkbcommon-x11-0 \
    libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 \
    libxcb-xinerama0 libxcb-xfixes0 libxcb-shape0 libxcb-randr0 \
    libxcb-sync1 libxcb-xkb1 libx11-xcb1 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal \
    C_INCLUDE_PATH=/usr/include/gdal \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install Python deps first (cache layer)
COPY requirement.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirement.txt

# Install package in editable mode
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

# Copy config templates and data
COPY configs_json/ ./configs_json/
COPY Ecospace_outputs/ ./Ecospace_outputs/

# Non-root user
RUN useradd -m -u 1000 fibe && chown -R fibe:fibe /app
USER fibe

# Entrypoint script
COPY --chown=fibe:fibe docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["configs_json/config_default.json"]