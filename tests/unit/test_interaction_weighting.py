from __future__ import annotations

from app.core.config import Settings
from app.db.models.interaction import InteractionType
from app.services import interaction_service


def test_weights_come_from_config(monkeypatch):
    custom = Settings(
        interaction_weight_like=7.0,
        interaction_weight_dislike=-9.0,
        interaction_weight_view=0.5,
    )
    monkeypatch.setattr(interaction_service, "get_settings", lambda: custom)

    assert interaction_service.interaction_weight(InteractionType.LIKE) == 7.0
    assert interaction_service.interaction_weight(InteractionType.DISLIKE) == -9.0
    assert interaction_service.interaction_weight(InteractionType.VIEW) == 0.5


def test_every_interaction_type_has_a_weight(monkeypatch):
    monkeypatch.setattr(interaction_service, "get_settings", Settings)
    for t in InteractionType:
        assert isinstance(interaction_service.interaction_weight(t), float)


def test_default_sign_convention():
    s = Settings()
    w = s.interaction_weights
    assert w["LIKE"] > 0 and w["SAVE"] > 0 and w["SHARE"] > 0
    assert w["SKIP"] < 0 and w["DISLIKE"] < 0
