"""数据层测试——种子数据 & 配置"""
import pytest
from data.seed.data import HS_CODES, TARIFF_SCHEDULES, SANCTIONS


class TestSeedData:
    def test_hs_codes_have_required_fields(self):
        for item in HS_CODES:
            assert "code" in item
            assert "description" in item
            assert "chapter" in item
            assert "heading" in item
            assert len(item["code"]) >= 6

    def test_hs_codes_no_duplicates(self):
        codes = [d["code"] for d in HS_CODES]
        assert len(codes) == len(set(codes))

    def test_tariff_schedules_have_required(self):
        for item in TARIFF_SCHEDULES:
            assert "country" in item
            assert "hs_code_prefix" in item
            assert "base_rate" in item

    def test_sanctions_have_required(self):
        for item in SANCTIONS:
            assert "entity_name" in item
            assert "list_type" in item


class TestConfig:
    def test_default_settings(self):
        from shared.config import settings
        assert settings.app_host == "127.0.0.1"
        assert settings.app_port == 8000
        assert settings.llm_model == "qwen-plus"

    def test_mysql_url_format(self):
        from shared.config import Settings
        s = Settings(mysql_user="tester", mysql_password="pwd",
                     mysql_host="db", mysql_port=3306, mysql_database="testdb")
        url = s.mysql_url
        assert "tester:pwd" in url
        assert "@db:3306" in url
        assert "/testdb" in url
        assert url.startswith("mysql+asyncmy://")

    def test_dashscope_key_from_env(self, monkeypatch):
        monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-123")
        from shared.config import Settings
        s = Settings()
        assert s.llm_api_key == "sk-test-123"

    def test_mysql_url_custom_host(self):
        from shared.config import Settings
        s = Settings(mysql_host="db.example.com", mysql_port=3307,
                     mysql_user="usr", mysql_password="pwd", mysql_database="mydb")
        assert "db.example.com:3307" in s.mysql_url
        assert "/mydb" in s.mysql_url
