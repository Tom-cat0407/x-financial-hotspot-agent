from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.types import JSON


Base = declarative_base()
JSONType = JSON().with_variant(JSONB, "postgresql")


class PipelineState(Base):
    __tablename__ = "pipeline_state"

    key = Column(String(80), primary_key=True)
    payload = Column(JSONType, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RunEvent(Base):
    __tablename__ = "run_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    state = Column(String(80), index=True)
    message = Column(Text)
    payload = Column(JSONType, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class RawPost(Base):
    __tablename__ = "raw_posts"

    post_id = Column(String(120), primary_key=True)
    author_handle = Column(String(120), index=True)
    source_type = Column(String(60), index=True)
    text = Column(Text)
    payload = Column(JSONType, nullable=False)
    created_at = Column(String(80))
    fetched_at = Column(String(80), default="")


class EventCluster(Base):
    __tablename__ = "event_clusters"

    cluster_id = Column(String(120), primary_key=True)
    main_title = Column(Text)
    event_type = Column(String(80), index=True)
    hot_score = Column(Float, default=0)
    confidence_score = Column(Float, default=0)
    payload = Column(JSONType, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ArtifactRecord(Base):
    __tablename__ = "artifact_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_type = Column(String(80), index=True)
    external_id = Column(String(160), index=True)
    payload = Column(JSONType, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
