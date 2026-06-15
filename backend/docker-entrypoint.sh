#!/bin/bash
set -e

echo "==> AgenticCustoms Docker Entrypoint"

# 等待 MySQL 就绪（最多 60 秒）
if [ -n "$MYSQL_HOST" ]; then
  echo "==> Waiting for MySQL at $MYSQL_HOST:$MYSQL_PORT ..."
  for i in $(seq 1 30); do
    if python -c "
import asyncio, sys
from sqlalchemy.ext.asyncio import create_async_engine
async def check():
    try:
        engine = create_async_engine('mysql+asyncmy://$MYSQL_USER:$MYSQL_PASSWORD@$MYSQL_HOST:$MYSQL_PORT/$MYSQL_DATABASE')
        async with engine.connect() as conn:
            await conn.execute('SELECT 1')
        sys.exit(0)
    except Exception:
        sys.exit(1)
asyncio.run(check())
" 2>/dev/null; then
      echo "==> MySQL is ready"
      break
    fi
    echo "    ... waiting ($i/30)"
    sleep 2
  done
fi

# 首次启动：灌入种子数据
echo "==> Running seed data..."
python -m data.seed.runner 2>/dev/null || echo "    (seed data skipped or already present)"

# 构建向量库（Chroma RAG）
echo "==> Building vector store..."
python -m rag.seed 2>/dev/null || echo "    (vector store skipped or already present)"

echo "==> Starting application..."
exec "$@"
