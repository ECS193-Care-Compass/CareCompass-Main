FROM public.ecr.aws/lambda/python:3.11

# Upgrade pip
RUN pip install --upgrade pip --quiet

# Install pysqlite3-binary for ChromaDB (Lambda's sqlite3 is too old)
RUN pip install pysqlite3-binary --quiet

# Copy requirements and install dependencies (pre-built wheels only)
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install -r ${LAMBDA_TASK_ROOT}/requirements.txt --quiet

# Patch: make chromadb use pysqlite3 instead of built-in sqlite3
RUN CHROMA_INIT=$(python -c "import importlib.util; print(importlib.util.find_spec('chromadb').origin)") && \
    echo '__import__("pysqlite3"); import sys; sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")' | cat - "$CHROMA_INIT" > /tmp/patched_init.py && \
    mv /tmp/patched_init.py "$CHROMA_INIT"

# Copy Lambda handler
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/
COPY s3_manager.py ${LAMBDA_TASK_ROOT}/

# Copy backend source code
COPY build/src/ ${LAMBDA_TASK_ROOT}/src/
COPY build/config/ ${LAMBDA_TASK_ROOT}/config/
COPY build/main.py ${LAMBDA_TASK_ROOT}/

CMD ["lambda_handler.lambda_handler"]