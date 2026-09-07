"""Aggregates all versioned API sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import admin, articles, feed, interactions, stories, users

api_router = APIRouter()
api_router.include_router(users.router)
api_router.include_router(articles.router)
api_router.include_router(stories.router)
api_router.include_router(feed.router)
api_router.include_router(interactions.router)
api_router.include_router(admin.router)
