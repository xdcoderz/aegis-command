FROM python:3.13-slim AS oqs-builder

ARG LIBOQS_VERSION=0.16.0
ARG LIBOQS_PYTHON_COMMIT=35eceb69d2b363cb0421085cf1ae1c682dee1acc

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git ninja-build libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch ${LIBOQS_VERSION} https://github.com/open-quantum-safe/liboqs.git /tmp/liboqs \
    && cmake -S /tmp/liboqs -B /tmp/liboqs/build -GNinja \
      -DBUILD_SHARED_LIBS=ON -DOQS_BUILD_ONLY_LIB=ON -DCMAKE_BUILD_TYPE=Release \
    && cmake --build /tmp/liboqs/build --parallel \
    && cmake --install /tmp/liboqs/build

RUN git clone https://github.com/open-quantum-safe/liboqs-python.git /tmp/liboqs-python \
    && cd /tmp/liboqs-python \
    && git checkout ${LIBOQS_PYTHON_COMMIT} \
    && pip install --no-cache-dir --prefix=/install .

FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LD_LIBRARY_PATH=/usr/local/lib \
    OQS_INSTALL_PATH=/usr/local \
    FINSPARK_PQC_REQUIRED=true

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 finspark \
    && useradd --uid 10001 --gid finspark --create-home finspark

COPY --from=oqs-builder /usr/local/lib/ /usr/local/lib/
COPY --from=oqs-builder /install/ /usr/local/

WORKDIR /app
COPY apps/api/pyproject.toml apps/api/README.md ./
COPY apps/api/src ./src
RUN pip install --no-cache-dir .

USER finspark
EXPOSE 8000
CMD ["fastapi", "run", "src/finspark/main.py", "--host", "0.0.0.0", "--port", "8000"]
