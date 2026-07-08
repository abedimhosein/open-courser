"""Tests for template tags."""

from django.test import TestCase

from apps.courses.templatetags.course_extras import duration


class TestDurationFilter(TestCase):
    def test_hours_minutes_seconds(self):
        assert duration(3661) == "1h 1m 1s"

    def test_minutes_only(self):
        assert duration(120) == "2m"

    def test_seconds_only(self):
        assert duration(45) == "45s"

    def test_zero(self):
        assert duration(0) == "0s"

    def test_none_returns_dash(self):
        assert duration(None) == "\u2014"

    def test_large_duration(self):
        result = duration(7200)
        assert "2h" in result

    def test_accepts_float(self):
        result = duration(65.7)
        assert "1m" in result
        assert "5s" in result
