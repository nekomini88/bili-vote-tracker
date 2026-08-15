# -*- coding: utf-8 -*-
"""Bili Vote Tracker — 单元测试 (不依赖运行中容器, 纯逻辑 + 临时DB)
运行: python3 -m pytest tests/ -v  (需 fastapi 依赖)
"""
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

# 容器路径不存在, mock StaticFiles 挂载 (import 前打补丁)
import starlette.staticfiles as _ssf

class _FakeStaticFiles:
    def __init__(self, *a, **k):
        pass

_ssf.StaticFiles = _FakeStaticFiles
import fastapi.staticfiles as _fsf
_fsf.StaticFiles = _FakeStaticFiles

import app as bvt


class TestMetaKV:
    """set_meta/get_meta 读写 (临时 DB)"""

    def setup_method(self):
        fd, self.db = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self._old = bvt.DB_PATH
        bvt.DB_PATH = self.db
        bvt.init_db()

    def teardown_method(self):
        bvt.DB_PATH = self._old
        try:
            os.unlink(self.db)
        except OSError:
            pass

    def test_set_and_get(self):
        bvt.set_meta("last_cursor", "12345")
        assert bvt.get_meta("last_cursor") == "12345"

    def test_get_default_when_missing(self):
        assert bvt.get_meta("no_such_key") is None
        assert bvt.get_meta("no_such_key", "fallback") == "fallback"

    def test_upsert_overwrites(self):
        bvt.set_meta("k", "v1")
        bvt.set_meta("k", "v2")
        assert bvt.get_meta("k") == "v2"

    def test_value_type_stringified(self):
        bvt.set_meta("num", 42)
        assert bvt.get_meta("num") == "42"


class TestAdminAuth:
    """admin_auth 认证逻辑"""

    def test_wrong_credentials_raises(self):
        from fastapi import HTTPException
        from fastapi.security import HTTPBasicCredentials
        old_u, old_p = bvt.ADMIN_USER, bvt.ADMIN_PASS
        bvt.ADMIN_USER, bvt.ADMIN_PASS = "admin", "secret"
        try:
            # 正确凭据通过
            assert bvt.admin_auth(HTTPBasicCredentials(username="admin", password="secret")) == "admin"
            # 错误凭据抛 401
            try:
                bvt.admin_auth(HTTPBasicCredentials(username="admin", password="wrong"))
                assert False, "应抛出 401"
            except HTTPException as e:
                assert e.status_code == 401
        finally:
            bvt.ADMIN_USER, bvt.ADMIN_PASS = old_u, old_p


class TestPublicConfig:
    def test_public_config_shape(self):
        c = bvt.public_config()
        assert "poll_interval" in c
        assert "target_url" in c
