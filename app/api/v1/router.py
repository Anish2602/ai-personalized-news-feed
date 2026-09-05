"""Aggregates all versioned API sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import admin, articles, interactions, users

api_router = APIRouter()
api_router.include_router(users.router)
api_router.include_router(articles.router)
api_router.include_router(interactions.router)
api_router.include_router(admin.router)

# Phase 6: api_router.include_router(feed.router)    # GET  /feed
