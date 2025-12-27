"""
Comprehensive pytest tests for the Crypto Ticker Service.

Tests cover:
- CryptoTickerInfo dataclass
- CryptoTickerService class methods
- Block explorer URL generation
- Batch processing
- Supported currencies listing
- Edge cases and error handling
- Singleton instance management
"""

import pytest
from typing import Dict

from api.services.crypto_ticker_service import (
    CryptoTickerInfo,
    CryptoTickerService,
    BLOCK_EXPLORERS,
    CURRENCY_METADATA,
    get_crypto_ticker_service,
    set_crypto_ticker_service,
)


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def service():
    """Create a fresh CryptoTickerService instance for each test."""
    return CryptoTickerService()


@pytest.fixture
def bitcoin_addresses():
    """Valid Bitcoin addresses of various types."""
    return {
        "p2pkh": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
        "p2sh": "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy",
        "bech32": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
        "bech32m": "bc1p5d7rjq7g6rdk2yhzks9smlaqtedr4dekq08ge8ztwac72sfr9rusxg3297",
        "testnet": "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx",
    }


@pytest.fixture
def ethereum_addresses():
    """Valid Ethereum/EVM addresses."""
    return {
        "lowercase": "0x742d35cc6634c0532925a3b844bc9e7595f5ed0e",
        "uppercase": "0x742D35CC6634C0532925A3B844BC9E7595F5ED0E",
        "mixed": "0x742d35Cc6634C0532925a3b844Bc9e7595f5eD0e",
    }


@pytest.fixture
def various_crypto_addresses():
    """Valid addresses for various cryptocurrencies."""
    return {
        "ltc": "LM2WMpR1Rp6j3Sa59cMXMs1SPzj9eXpGc1",
        "doge": "D7Y55bkvqN29LYLxRq6Qjx5N7yx2cN4fY5",
        "xrp": "rN7n3473SaZBCG4dFL83w7a1RXtXtbk2D9",
        "ada": "addr1qxck8cqz7h5xmevz2j3e9lhfqfpw9h76mmwph3z7pxlcrhnq9n97mz5qx9z5kjq7jqxhz5ylqp5gf9zxqyxvz0qr0y5s0f5lzn",
        "sol": "7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV",
        "trx": "TJCnKsPa7y5okkXvQAidZBzqx3QyQ6sxMW",
        "xlm": "GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOUJ3B6EZZJLAP5V",
        "xmr": "44AFFq5kSiGBoZ4NMDwYtN18obc8AemS33DBLWs3H7otXft3XjrpDtQGv7SqSsaBYBb98uNbr2VBBEt7f2wfn3RVGQBEP3A",
        "atom": "cosmos1yl6hdjhmkf37639730gffanpzndzdpmhwlkfhr",
        "xtz": "tz1VSUr8wwNhLAzempoch5d6hLRiTh8Cjcjb",
    }


# ==============================================================================
# CryptoTickerInfo Tests
# ==============================================================================


class TestCryptoTickerInfo:
    """Tests for the CryptoTickerInfo dataclass."""

    def test_create_ticker_info(self):
        """Test creating a CryptoTickerInfo instance."""
        info = CryptoTickerInfo(
            address="bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
            currency="BTC",
            network="mainnet",
            ticker_symbol="BTC",
            display_name="Bitcoin",
            icon_class="fab fa-bitcoin",
            explorer_url="https://blockchair.com/bitcoin/address/bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
            is_valid=True,
            address_type="Bech32 (Native SegWit)",
            confidence=0.98,
        )

        assert info.address == "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
        assert info.currency == "BTC"
        assert info.network == "mainnet"
        assert info.ticker_symbol == "BTC"
        assert info.display_name == "Bitcoin"
        assert info.icon_class == "fab fa-bitcoin"
        assert info.explorer_url is not None
        assert info.is_valid is True
        assert info.address_type == "Bech32 (Native SegWit)"
        assert info.confidence == 0.98

    def test_ticker_info_defaults(self):
        """Test CryptoTickerInfo default values."""
        info = CryptoTickerInfo(
            address="test",
            currency="BTC",
            network="mainnet",
            ticker_symbol="BTC",
            display_name="Bitcoin",
            icon_class="fab fa-bitcoin",
        )

        assert info.explorer_url is None
        assert info.is_valid is True
        assert info.address_type is None
        assert info.confidence == 0.0

    def test_to_dict_method(self):
        """Test the to_dict method returns proper dictionary."""
        info = CryptoTickerInfo(
            address="bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
            currency="BTC",
            network="mainnet",
            ticker_symbol="BTC",
            display_name="Bitcoin",
            icon_class="fab fa-bitcoin",
            explorer_url="https://blockchair.com/bitcoin/address/bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
            is_valid=True,
            address_type="Bech32 (Native SegWit)",
            confidence=0.98,
        )

        result = info.to_dict()

        assert isinstance(result, dict)
        assert result["address"] == "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
        assert result["currency"] == "BTC"
        assert result["network"] == "mainnet"
        assert result["ticker_symbol"] == "BTC"
        assert result["display_name"] == "Bitcoin"
        assert result["icon_class"] == "fab fa-bitcoin"
        assert result["explorer_url"] is not None
        assert result["is_valid"] is True
        assert result["address_type"] == "Bech32 (Native SegWit)"
        assert result["confidence"] == 0.98

    def test_to_dict_serializable(self):
        """Test that to_dict result is JSON serializable."""
        import json

        info = CryptoTickerInfo(
            address="test",
            currency="BTC",
            network="mainnet",
            ticker_symbol="BTC",
            display_name="Bitcoin",
            icon_class="fab fa-bitcoin",
        )

        result = info.to_dict()
        json_str = json.dumps(result)

        assert isinstance(json_str, str)
        restored = json.loads(json_str)
        assert restored["currency"] == "BTC"


# ==============================================================================
# CryptoTickerService - get_ticker_info Tests
# ==============================================================================


class TestGetTickerInfo:
    """Tests for the get_ticker_info method."""

    def test_get_ticker_info_bitcoin_bech32(self, service, bitcoin_addresses):
        """Test getting ticker info for Bitcoin Bech32 address."""
        info = service.get_ticker_info(bitcoin_addresses["bech32"])

        assert info is not None
        assert info.currency == "BTC"
        assert info.ticker_symbol == "BTC"
        assert info.display_name == "Bitcoin"
        assert info.icon_class == "fab fa-bitcoin"
        assert info.network == "mainnet"
        assert info.is_valid is True
        assert info.confidence >= 0.98
        assert info.explorer_url is not None
        assert "blockchair.com" in info.explorer_url or "blockchain.com" in info.explorer_url

    def test_get_ticker_info_bitcoin_legacy(self, service, bitcoin_addresses):
        """Test getting ticker info for Bitcoin Legacy (P2PKH) address."""
        info = service.get_ticker_info(bitcoin_addresses["p2pkh"])

        assert info is not None
        assert info.currency == "BTC"
        assert info.display_name == "Bitcoin"
        assert "P2PKH" in info.address_type or "Legacy" in info.address_type

    def test_get_ticker_info_ethereum(self, service, ethereum_addresses):
        """Test getting ticker info for Ethereum address."""
        info = service.get_ticker_info(ethereum_addresses["lowercase"])

        assert info is not None
        assert info.currency == "ETH"
        assert info.ticker_symbol == "ETH"
        assert info.display_name == "Ethereum"
        assert info.icon_class == "fab fa-ethereum"
        assert info.address_type == "EVM Address"
        assert info.explorer_url is not None
        assert "etherscan.io" in info.explorer_url

    def test_get_ticker_info_litecoin(self, service, various_crypto_addresses):
        """Test getting ticker info for Litecoin address."""
        info = service.get_ticker_info(various_crypto_addresses["ltc"])

        assert info is not None
        assert info.currency == "LTC"
        assert info.display_name == "Litecoin"

    def test_get_ticker_info_dogecoin(self, service, various_crypto_addresses):
        """Test getting ticker info for Dogecoin address."""
        info = service.get_ticker_info(various_crypto_addresses["doge"])

        assert info is not None
        assert info.currency == "DOGE"
        assert info.display_name == "Dogecoin"

    def test_get_ticker_info_xrp(self, service, various_crypto_addresses):
        """Test getting ticker info for XRP address."""
        info = service.get_ticker_info(various_crypto_addresses["xrp"])

        assert info is not None
        assert info.currency == "XRP"
        assert info.display_name == "Ripple"

    def test_get_ticker_info_cardano(self, service, various_crypto_addresses):
        """Test getting ticker info for Cardano address."""
        info = service.get_ticker_info(various_crypto_addresses["ada"])

        assert info is not None
        assert info.currency == "ADA"
        assert info.display_name == "Cardano"

    def test_get_ticker_info_tron(self, service, various_crypto_addresses):
        """Test getting ticker info for Tron address."""
        info = service.get_ticker_info(various_crypto_addresses["trx"])

        assert info is not None
        assert info.currency == "TRX"
        assert info.display_name == "Tron"

    def test_get_ticker_info_stellar(self, service, various_crypto_addresses):
        """Test getting ticker info for Stellar address."""
        info = service.get_ticker_info(various_crypto_addresses["xlm"])

        assert info is not None
        assert info.currency == "XLM"
        assert info.display_name == "Stellar"

    def test_get_ticker_info_monero(self, service, various_crypto_addresses):
        """Test getting ticker info for Monero address."""
        info = service.get_ticker_info(various_crypto_addresses["xmr"])

        assert info is not None
        assert info.currency == "XMR"
        assert info.display_name == "Monero"

    def test_get_ticker_info_cosmos(self, service, various_crypto_addresses):
        """Test getting ticker info for Cosmos address."""
        info = service.get_ticker_info(various_crypto_addresses["atom"])

        assert info is not None
        assert info.currency == "ATOM"
        assert info.display_name == "Cosmos"

    def test_get_ticker_info_tezos(self, service, various_crypto_addresses):
        """Test getting ticker info for Tezos address."""
        info = service.get_ticker_info(various_crypto_addresses["xtz"])

        assert info is not None
        assert info.currency == "XTZ"
        assert info.display_name == "Tezos"

    def test_get_ticker_info_empty_string(self, service):
        """Test that empty string returns None."""
        info = service.get_ticker_info("")

        assert info is None

    def test_get_ticker_info_none(self, service):
        """Test that None returns None."""
        info = service.get_ticker_info(None)

        assert info is None

    def test_get_ticker_info_whitespace(self, service):
        """Test that whitespace-only string returns None."""
        info = service.get_ticker_info("   \t\n   ")

        assert info is None

    def test_get_ticker_info_invalid_address(self, service):
        """Test that invalid address returns None."""
        info = service.get_ticker_info("not_a_valid_crypto_address")

        assert info is None

    def test_get_ticker_info_with_leading_trailing_whitespace(self, service, bitcoin_addresses):
        """Test that addresses with whitespace are still detected."""
        info = service.get_ticker_info("   " + bitcoin_addresses["bech32"] + "   ")

        assert info is not None
        assert info.currency == "BTC"

    def test_get_ticker_info_non_string_input(self, service):
        """Test that non-string input returns None."""
        info = service.get_ticker_info(12345)

        assert info is None


# ==============================================================================
# CryptoTickerService - get_ticker_info_batch Tests
# ==============================================================================


class TestGetTickerInfoBatch:
    """Tests for the get_ticker_info_batch method."""

    def test_batch_with_valid_addresses(self, service, bitcoin_addresses, ethereum_addresses):
        """Test batch lookup with valid addresses."""
        addresses = [
            bitcoin_addresses["bech32"],
            ethereum_addresses["lowercase"],
        ]

        results = service.get_ticker_info_batch(addresses)

        assert len(results) == 2
        assert bitcoin_addresses["bech32"] in results
        assert ethereum_addresses["lowercase"] in results
        assert results[bitcoin_addresses["bech32"]].currency == "BTC"
        assert results[ethereum_addresses["lowercase"]].currency == "ETH"

    def test_batch_with_mixed_valid_invalid(self, service, bitcoin_addresses):
        """Test batch lookup with mix of valid and invalid addresses."""
        addresses = [
            bitcoin_addresses["bech32"],
            "invalid_address",
            "another_invalid",
        ]

        results = service.get_ticker_info_batch(addresses)

        assert len(results) == 1
        assert bitcoin_addresses["bech32"] in results
        assert "invalid_address" not in results

    def test_batch_with_all_invalid(self, service):
        """Test batch lookup with all invalid addresses."""
        # Use addresses that don't match any crypto pattern
        # (EOS pattern is very permissive, so use strings with special chars)
        addresses = ["not-valid-@#$", "another!invalid", "123-456-789-abc"]

        results = service.get_ticker_info_batch(addresses)

        assert len(results) == 0

    def test_batch_with_empty_list(self, service):
        """Test batch lookup with empty list."""
        results = service.get_ticker_info_batch([])

        assert len(results) == 0

    def test_batch_with_none_values(self, service, bitcoin_addresses):
        """Test batch lookup handles None values in list."""
        addresses = [bitcoin_addresses["bech32"], None, ""]

        results = service.get_ticker_info_batch(addresses)

        assert len(results) == 1

    def test_batch_with_duplicates(self, service, bitcoin_addresses):
        """Test batch lookup with duplicate addresses."""
        addresses = [
            bitcoin_addresses["bech32"],
            bitcoin_addresses["bech32"],
        ]

        results = service.get_ticker_info_batch(addresses)

        # Should have one result (deduped by the dict)
        assert bitcoin_addresses["bech32"] in results

    def test_batch_returns_crypto_ticker_info(self, service, bitcoin_addresses):
        """Test that batch results contain CryptoTickerInfo instances."""
        addresses = [bitcoin_addresses["bech32"]]

        results = service.get_ticker_info_batch(addresses)

        for address, info in results.items():
            assert isinstance(info, CryptoTickerInfo)

    def test_batch_many_addresses(self, service, various_crypto_addresses):
        """Test batch lookup with many different cryptocurrencies."""
        addresses = list(various_crypto_addresses.values())

        results = service.get_ticker_info_batch(addresses)

        assert len(results) >= 5  # At least some should be detected


# ==============================================================================
# CryptoTickerService - get_supported_currencies Tests
# ==============================================================================


class TestGetSupportedCurrencies:
    """Tests for the get_supported_currencies method."""

    def test_returns_list(self, service):
        """Test that function returns a list."""
        result = service.get_supported_currencies()

        assert isinstance(result, list)

    def test_returns_non_empty_list(self, service):
        """Test that the list is not empty."""
        result = service.get_supported_currencies()

        assert len(result) > 0

    def test_each_item_has_required_fields(self, service):
        """Test that each item has required fields."""
        result = service.get_supported_currencies()

        for item in result:
            assert "ticker_symbol" in item
            assert "display_name" in item
            assert "icon_class" in item
            assert "has_explorer" in item
            assert isinstance(item["ticker_symbol"], str)
            assert isinstance(item["display_name"], str)
            assert isinstance(item["icon_class"], str)
            assert isinstance(item["has_explorer"], bool)

    def test_includes_major_cryptocurrencies(self, service):
        """Test that major cryptocurrencies are included."""
        result = service.get_supported_currencies()
        tickers = {item["ticker_symbol"] for item in result}

        assert "BTC" in tickers
        assert "ETH" in tickers
        assert "LTC" in tickers
        assert "DOGE" in tickers

    def test_icon_classes_are_fontawesome_format(self, service):
        """Test that icon classes follow FontAwesome format."""
        result = service.get_supported_currencies()

        for item in result:
            icon = item["icon_class"]
            # Should start with fa- or fab or fas
            assert icon.startswith("fa") or icon.startswith("fas") or icon.startswith("fab")


# ==============================================================================
# CryptoTickerService - format_explorer_url Tests
# ==============================================================================


class TestFormatExplorerUrl:
    """Tests for the format_explorer_url method."""

    def test_format_bitcoin_mainnet_url(self, service):
        """Test generating Bitcoin mainnet explorer URL."""
        address = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
        url = service.format_explorer_url(address, "BTC", "mainnet")

        assert url is not None
        assert len(url) > 0
        assert address in url
        assert "blockchair.com" in url or "blockchain.com" in url

    def test_format_ethereum_mainnet_url(self, service):
        """Test generating Ethereum mainnet explorer URL."""
        address = "0x742d35cc6634c0532925a3b844bc9e7595f5ed0e"
        url = service.format_explorer_url(address, "ETH", "mainnet")

        assert url is not None
        assert address in url
        assert "etherscan.io" in url

    def test_format_bitcoin_testnet_url(self, service):
        """Test generating Bitcoin testnet explorer URL."""
        address = "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx"
        url = service.format_explorer_url(address, "BTC", "testnet")

        assert url is not None
        assert address in url
        assert "blockstream.info" in url or "testnet" in url

    def test_format_url_fallback_to_mainnet(self, service):
        """Test that unknown network falls back to mainnet."""
        address = "0x742d35cc6634c0532925a3b844bc9e7595f5ed0e"
        url = service.format_explorer_url(address, "ETH", "unknown_network")

        assert url is not None
        assert "etherscan.io" in url

    def test_format_url_unknown_currency(self, service):
        """Test that unknown currency returns empty string."""
        url = service.format_explorer_url("address", "UNKNOWN_COIN", "mainnet")

        assert url == ""

    def test_format_url_case_insensitive_currency(self, service):
        """Test that currency is case-insensitive."""
        address = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"

        url_upper = service.format_explorer_url(address, "BTC", "mainnet")
        url_lower = service.format_explorer_url(address, "btc", "mainnet")

        assert url_upper == url_lower

    def test_format_url_various_currencies(self, service):
        """Test explorer URL generation for various currencies."""
        test_cases = [
            ("LM2WMpR1Rp6j3Sa59cMXMs1SPzj9eXpGc1", "LTC", "blockchair.com"),
            ("D7Y55bkvqN29LYLxRq6Qjx5N7yx2cN4fY5", "DOGE", "dogechain.info"),
            ("rN7n3473SaZBCG4dFL83w7a1RXtXtbk2D9", "XRP", "xrpscan.com"),
            ("TJCnKsPa7y5okkXvQAidZBzqx3QyQ6sxMW", "TRX", "tronscan.org"),
        ]

        for address, currency, expected_domain in test_cases:
            url = service.format_explorer_url(address, currency, "mainnet")
            assert expected_domain in url, f"Expected {expected_domain} in URL for {currency}"


# ==============================================================================
# Block Explorer Configuration Tests
# ==============================================================================


class TestBlockExplorerConfig:
    """Tests for the BLOCK_EXPLORERS configuration."""

    def test_major_currencies_have_explorers(self):
        """Test that major currencies have block explorer configurations."""
        required_currencies = ["bitcoin", "ethereum", "litecoin", "dogecoin"]

        for currency in required_currencies:
            assert currency in BLOCK_EXPLORERS, f"{currency} missing from BLOCK_EXPLORERS"
            assert "mainnet" in BLOCK_EXPLORERS[currency], f"{currency} missing mainnet explorer"

    def test_explorer_urls_contain_placeholder(self):
        """Test that explorer URLs contain {address} placeholder."""
        for currency, networks in BLOCK_EXPLORERS.items():
            for network, url in networks.items():
                assert "{address}" in url, f"{currency}/{network} URL missing {{address}} placeholder"

    def test_explorer_urls_are_https(self):
        """Test that explorer URLs use HTTPS."""
        for currency, networks in BLOCK_EXPLORERS.items():
            for network, url in networks.items():
                assert url.startswith("https://"), f"{currency}/{network} URL should use HTTPS"


# ==============================================================================
# Currency Metadata Configuration Tests
# ==============================================================================


class TestCurrencyMetadataConfig:
    """Tests for the CURRENCY_METADATA configuration."""

    def test_major_currencies_have_metadata(self):
        """Test that major currencies have metadata configured."""
        required_tickers = ["BTC", "ETH", "LTC", "DOGE", "XRP", "ADA", "SOL"]

        for ticker in required_tickers:
            assert ticker in CURRENCY_METADATA, f"{ticker} missing from CURRENCY_METADATA"

    def test_metadata_has_required_fields(self):
        """Test that each metadata entry has required fields."""
        for ticker, metadata in CURRENCY_METADATA.items():
            assert "display_name" in metadata, f"{ticker} missing display_name"
            assert "icon_class" in metadata, f"{ticker} missing icon_class"
            assert "currency_key" in metadata, f"{ticker} missing currency_key"

    def test_display_names_are_proper(self):
        """Test that display names are properly formatted."""
        expected = {
            "BTC": "Bitcoin",
            "ETH": "Ethereum",
            "LTC": "Litecoin",
            "DOGE": "Dogecoin",
        }

        for ticker, expected_name in expected.items():
            assert CURRENCY_METADATA[ticker]["display_name"] == expected_name


# ==============================================================================
# Singleton Instance Tests
# ==============================================================================


class TestSingletonInstance:
    """Tests for singleton instance management."""

    def test_get_crypto_ticker_service_returns_instance(self):
        """Test that get_crypto_ticker_service returns an instance."""
        service = get_crypto_ticker_service()

        assert service is not None
        assert isinstance(service, CryptoTickerService)

    def test_get_crypto_ticker_service_returns_same_instance(self):
        """Test that multiple calls return the same instance."""
        service1 = get_crypto_ticker_service()
        service2 = get_crypto_ticker_service()

        assert service1 is service2

    def test_set_crypto_ticker_service(self):
        """Test that set_crypto_ticker_service works."""
        original = get_crypto_ticker_service()

        new_service = CryptoTickerService()
        set_crypto_ticker_service(new_service)

        current = get_crypto_ticker_service()
        assert current is new_service

        # Restore original
        set_crypto_ticker_service(original)

    def test_set_crypto_ticker_service_to_none(self):
        """Test setting service to None."""
        original = get_crypto_ticker_service()

        set_crypto_ticker_service(None)

        # Getting service should create new instance
        new_service = get_crypto_ticker_service()
        assert new_service is not None
        assert isinstance(new_service, CryptoTickerService)

        # Restore
        set_crypto_ticker_service(original)


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestIntegration:
    """Integration tests combining multiple features."""

    def test_full_workflow_single_address(self, service, bitcoin_addresses):
        """Test typical workflow for single address analysis."""
        address = bitcoin_addresses["bech32"]

        # Get ticker info
        info = service.get_ticker_info(address)

        assert info is not None
        assert info.currency == "BTC"

        # Serialize to dict
        data = info.to_dict()

        assert data["currency"] == "BTC"
        assert data["explorer_url"] is not None

        # Verify explorer URL is properly formatted
        assert address in data["explorer_url"]

    def test_full_workflow_batch_analysis(self, service, various_crypto_addresses):
        """Test batch analysis workflow."""
        addresses = list(various_crypto_addresses.values())

        # Batch lookup
        results = service.get_ticker_info_batch(addresses)

        # Verify we got results
        assert len(results) > 0

        # Verify each result can be serialized
        for address, info in results.items():
            data = info.to_dict()
            assert data["address"] == address
            assert data["currency"] is not None
            assert data["is_valid"] is True

    def test_service_reusability(self, service, bitcoin_addresses, ethereum_addresses):
        """Test that service can be reused for multiple lookups."""
        # First lookup
        btc_info = service.get_ticker_info(bitcoin_addresses["bech32"])

        # Second lookup (different crypto)
        eth_info = service.get_ticker_info(ethereum_addresses["lowercase"])

        # Third lookup (same as first)
        btc_info2 = service.get_ticker_info(bitcoin_addresses["bech32"])

        assert btc_info.currency == "BTC"
        assert eth_info.currency == "ETH"
        assert btc_info2.currency == "BTC"

    def test_explorer_url_consistency(self, service, bitcoin_addresses):
        """Test that explorer URLs are consistent."""
        address = bitcoin_addresses["bech32"]

        # Get via ticker info
        info = service.get_ticker_info(address)
        url_from_info = info.explorer_url

        # Get directly
        url_direct = service.format_explorer_url(address, "BTC", "mainnet")

        # Both should point to the same explorer
        assert url_from_info is not None
        assert url_direct is not None
        # Both should contain the address
        assert address in url_from_info
        assert address in url_direct


# ==============================================================================
# Edge Cases and Error Handling Tests
# ==============================================================================


class TestEdgeCasesAndErrors:
    """Tests for edge cases and error handling."""

    def test_very_long_address(self, service):
        """Test handling of very long strings."""
        long_string = "a" * 10000
        info = service.get_ticker_info(long_string)

        # Should complete without exception
        assert info is None  # Not a valid address

    def test_unicode_in_address(self, service):
        """Test handling of Unicode characters."""
        info = service.get_ticker_info("bitcoin_address_unicode")

        assert info is None

    def test_special_characters(self, service):
        """Test handling of special characters."""
        info = service.get_ticker_info("!@#$%^&*()_+{}|:<>?")

        assert info is None

    def test_sql_injection_attempt(self, service):
        """Test that SQL injection attempts don't cause issues."""
        info = service.get_ticker_info("'; DROP TABLE addresses; --")

        assert info is None

    def test_html_injection_attempt(self, service):
        """Test that HTML injection attempts don't cause issues."""
        info = service.get_ticker_info("<script>alert('xss')</script>")

        assert info is None

    def test_batch_with_very_large_list(self, service, bitcoin_addresses):
        """Test batch processing with large list."""
        # Create list of 50 addresses (mix of valid and invalid)
        # Note: batch returns a dict, so duplicate addresses are deduplicated
        addresses = []
        for i in range(50):
            if i % 5 == 0:
                addresses.append(bitcoin_addresses["bech32"])  # Same address repeated
            else:
                # Use addresses with special chars that won't match any pattern
                addresses.append(f"invalid@address#{i}!")

        results = service.get_ticker_info_batch(addresses)

        # Should have 1 valid result (duplicates are deduplicated in dict)
        assert len(results) == 1
        assert bitcoin_addresses["bech32"] in results

    def test_batch_with_mixed_types(self, service, bitcoin_addresses):
        """Test batch with non-string types (should handle gracefully)."""
        addresses = [
            bitcoin_addresses["bech32"],
            123,  # Non-string
            None,
            "",
            [],  # List
        ]

        results = service.get_ticker_info_batch(addresses)

        # Should only have one valid result
        assert len(results) == 1
