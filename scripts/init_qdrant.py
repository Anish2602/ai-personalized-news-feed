"""Create the Qdrant collection if it does not exist.

Optional — the vector store also creates it lazily on first write. Run this to
provision it up front:  ``python -m scripts.init_qdrant``
"""

from __future__ import annotations

import asyncio

from app.vector.client import vector_store


async def _main() -> None:
    async with vector_store() as store:
        await store.ensure_collection()
    print("qdrant collection ready")


if __name__ == "__main__":
    asyncio.run(_main())
