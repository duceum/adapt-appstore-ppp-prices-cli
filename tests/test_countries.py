import csv
import tempfile
from pathlib import Path

from appstore_ppp_prices.countries import Country, MINIMUM_PRICE_HIGH, MINIMUM_PRICE_LOW, load_countries


def _write_csv(rows: list[dict], path: Path):
    fields = ["country_code", "country_name", "gdp_per_capita", "category", "default_coefficient"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class TestCountryMinimumPrice:
    def test_premium_returns_high(self):
        c = Country(code="LUX", name="Luxembourg", gdp_per_capita=146818, category="premium", default_coefficient=1.10)
        assert c.minimum_price == MINIMUM_PRICE_HIGH

    def test_usa_returns_high(self):
        c = Country(code="USA", name="United States", gdp_per_capita=80000, category="usa", default_coefficient=1.00)
        assert c.minimum_price == MINIMUM_PRICE_HIGH

    def test_high_income_returns_high(self):
        c = Country(code="DEU", name="Germany", gdp_per_capita=55000, category="high_income", default_coefficient=0.85)
        assert c.minimum_price == MINIMUM_PRICE_HIGH

    def test_upper_middle_returns_low(self):
        c = Country(code="POL", name="Poland", gdp_per_capita=18000, category="upper_middle", default_coefficient=0.675)
        assert c.minimum_price == MINIMUM_PRICE_LOW

    def test_lower_middle_returns_low(self):
        c = Country(code="BRA", name="Brazil", gdp_per_capita=9000, category="lower_middle", default_coefficient=0.50)
        assert c.minimum_price == MINIMUM_PRICE_LOW

    def test_emerging_returns_low(self):
        c = Country(code="IND", name="India", gdp_per_capita=2818, category="emerging", default_coefficient=0.40)
        assert c.minimum_price == MINIMUM_PRICE_LOW


class TestLoadCountries:
    def test_loads_from_csv(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        _write_csv([
            {"country_code": "DEU", "country_name": "Germany", "gdp_per_capita": "55000", "category": "high_income", "default_coefficient": "0.85"},
            {"country_code": "IND", "country_name": "India", "gdp_per_capita": "2818", "category": "emerging", "default_coefficient": "0.40"},
        ], csv_path)
        countries = load_countries(csv_path=csv_path)
        assert len(countries) == 2
        assert countries[0].code == "DEU"
        assert countries[0].gdp_per_capita == 55000
        assert countries[1].default_coefficient == 0.40

    def test_excludes_usa(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        _write_csv([
            {"country_code": "USA", "country_name": "United States", "gdp_per_capita": "80000", "category": "usa", "default_coefficient": "1.00"},
            {"country_code": "DEU", "country_name": "Germany", "gdp_per_capita": "55000", "category": "high_income", "default_coefficient": "0.85"},
        ], csv_path)
        countries = load_countries(csv_path=csv_path)
        assert len(countries) == 1
        assert countries[0].code == "DEU"

    def test_excludes_specified_countries(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        _write_csv([
            {"country_code": "DEU", "country_name": "Germany", "gdp_per_capita": "55000", "category": "high_income", "default_coefficient": "0.85"},
            {"country_code": "IND", "country_name": "India", "gdp_per_capita": "2818", "category": "emerging", "default_coefficient": "0.40"},
            {"country_code": "BRA", "country_name": "Brazil", "gdp_per_capita": "9000", "category": "lower_middle", "default_coefficient": "0.50"},
        ], csv_path)
        countries = load_countries(exclude={"DEU", "BRA"}, csv_path=csv_path)
        assert len(countries) == 1
        assert countries[0].code == "IND"

    def test_exclude_case_insensitive(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        _write_csv([
            {"country_code": "DEU", "country_name": "Germany", "gdp_per_capita": "55000", "category": "high_income", "default_coefficient": "0.85"},
        ], csv_path)
        countries = load_countries(exclude={"deu"}, csv_path=csv_path)
        assert len(countries) == 0

    def test_empty_csv(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        _write_csv([], csv_path)
        countries = load_countries(csv_path=csv_path)
        assert countries == []

    def test_skips_corrupt_gdp(self, tmp_path):
        """Rows with non-numeric GDP should be skipped, not crash."""
        csv_path = tmp_path / "test.csv"
        _write_csv([
            {"country_code": "DEU", "country_name": "Germany", "gdp_per_capita": "55000", "category": "high_income", "default_coefficient": "0.85"},
            {"country_code": "BAD", "country_name": "Badland", "gdp_per_capita": "not_a_number", "category": "emerging", "default_coefficient": "0.40"},
        ], csv_path)
        countries = load_countries(csv_path=csv_path)
        assert len(countries) == 1
        assert countries[0].code == "DEU"

    def test_skips_corrupt_coefficient(self, tmp_path):
        """Rows with non-numeric coefficient should be skipped, not crash."""
        csv_path = tmp_path / "test.csv"
        _write_csv([
            {"country_code": "DEU", "country_name": "Germany", "gdp_per_capita": "55000", "category": "high_income", "default_coefficient": "abc"},
            {"country_code": "IND", "country_name": "India", "gdp_per_capita": "2818", "category": "emerging", "default_coefficient": "0.40"},
        ], csv_path)
        countries = load_countries(csv_path=csv_path)
        assert len(countries) == 1
        assert countries[0].code == "IND"

    def test_real_csv_excludes_usa(self):
        """Verify real countries.csv doesn't include USA in results."""
        countries = load_countries()
        codes = {c.code for c in countries}
        assert "USA" not in codes
        assert len(countries) > 100  # sanity check
