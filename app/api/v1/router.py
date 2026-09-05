"""Aggregates all versioned API sub-routers.

Endpoint modules (users, articles, feed, interactions) are added in later phases.
"""

from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter()

# Phase 2+: api_router.include_router(users.router)
#           api_router.include_router(articles.router)
#           api_router.include_router(interactions.router)
#           api_router.include_router(feed.router)
