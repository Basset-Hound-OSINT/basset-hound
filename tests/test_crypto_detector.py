"""
Comprehensive pytest tests for the cryptocurrency address detection utility.

Tests cover:
- Bitcoin addresses (P2PKH, P2SH, Bech32, Bech32m/Taproot)
- Ethereum and EVM addresses
- Litecoin addresses
- Dogecoin addresses
- XRP/Ripple addresses
- Cardano addresses (Shelley, Byron)
- Solana addresses
- Monero addresses
- Tron addresses
- Stellar addresses
- Invalid/malformed addresses
- Edge cases (empty strings, None, special characters)
- detect_all_possible function for ambiguous addresses
- get_supported_cryptocurrencies function
"""

import pytest
from api.utils.crypto_detector import (
    CryptoAddressDetector,
    CryptoDetectionResult,
    detect_crypto_address,
    detect_all_crypto_addresses,
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def detector():
    """Create a fresh CryptoAddressDetector instance for each test."""
    return CryptoAddressDetector()


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
def litecoin_addresses():
    """Valid Litecoin addresses of various types."""
    return {
        "p2pkh": "LM2WMpR1Rp6j3Sa59cMXMs1SPzj9eXpGc1",
        "p2sh": "MQ47VqWkWCnpJj3wZRJj8jYb4RqBGP8Yfe",
        "bech32": "ltc1qw508d6qejxtdg4y5r3zarvary0c5xw7kgmn4n9",
    }


@pytest.fixture
def dogecoin_addresses():
    """Valid Dogecoin addresses."""
    return {
        "p2pkh": "D7Y55bkvqN29LYLxRq6Qjx5N7yx2cN4fY5",
        "p2sh": "A7Y55bkvqN29LYLxRq6Qjx5N7yx2cN4fY5",
    }


@pytest.fixture
def xrp_addresses():
    """Valid XRP/Ripple addresses."""
    return {
        "classic": "rN7n3473SaZBCG4dFL83w7a1RXtXtbk2D9",
        "x_address": "X7gJ5YK8abHf2eTPWPFHAAot8Knck11QGqmQ7a6a3Z8PJvk",
    }


@pytest.fixture
def cardano_addresses():
    """Valid Cardano addresses."""
    return {
        "shelley": "addr1qxck8cqz7h5xmevz2j3e9lhfqfpw9h76mmwph3z7pxlcrhnq9n97mz5qx9z5kjq7jqxhz5ylqp5gf9zxqyxvz0qr0y5s0f5lzn",
        "byron_icarus": "Ae2tdPwUPEZFRbhH9XzBZjNq5JJhvkNxdBJ8CuPNvJRjGzQ8c3vA6nq7vZB",
        "byron_daedalus": "DdzFFzCqrhsfYMUNRxtQ5NNKbWVw4ZJBxrZPxYGHVLJBHqnVTf9CZmW7xjJJTqc8HqD9ggJgHMsqRPJKDKGEKRBNQFvFnKYFXopxb9Sx",
    }


@pytest.fixture
def solana_addresses():
    """Valid Solana addresses."""
    return {
        "standard": "7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV",
        "longer": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    }


@pytest.fixture
def monero_addresses():
    """Valid Monero addresses."""
    return {
        "standard": "44AFFq5kSiGBoZ4NMDwYtN18obc8AemS33DBLWs3H7otXft3XjrpDtQGv7SqSsaBYBb98uNbr2VBBEt7f2wfn3RVGQBEP3A",
        "subaddress": "82VJpHPNPmVUxzJDYKghZLBFQrCJfbZP9bxvxo5j5VLzBvNcXnPFWxY2D75nh4rH5L1d2PLRJFxU3GqpYVkXGxU8Hs7FrTu",
    }


@pytest.fixture
def tron_addresses():
    """Valid Tron addresses."""
    return {
        "standard": "TJCnKsPa7y5okkXvQAidZBzqx3QyQ6sxMW",
    }


@pytest.fixture
def stellar_addresses():
    """Valid Stellar addresses."""
    return {
        "standard": "GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOUJ3B6EZZJLAP5V",
    }


# ==============================================================================
# Bitcoin Address Tests
# ==============================================================================

class TestBitcoinAddresses:
    """Tests for Bitcoin address detection."""

    def test_detect_p2pkh_legacy_address(self, detector, bitcoin_addresses):
        """Test detection of P2PKH (Legacy) Bitcoin address starting with 1."""
        result = detector.detect(bitcoin_addresses["p2pkh"])

        assert result.detected is True
        assert result.coin_ticker == "BTC"
        assert result.coin_name == "Bitcoin"
        assert result.network == "mainnet"
        assert "P2PKH" in result.address_type or "Legacy" in result.address_type
        assert result.confidence >= 0.95
        assert "blockchain.com" in result.explorer_url

    def test_detect_p2sh_segwit_address(self, detector, bitcoin_addresses):
        """Test detection of P2SH (SegWit compatible) Bitcoin address starting with 3."""
        result = detector.detect(bitcoin_addresses["p2sh"])

        assert result.detected is True
        assert result.coin_ticker == "BTC"
        assert result.coin_name == "Bitcoin"
        assert result.network == "mainnet"
        assert "P2SH" in result.address_type or "SegWit" in result.address_type
        assert result.confidence >= 0.95

    def test_detect_bech32_native_segwit_address(self, detector, bitcoin_addresses):
        """Test detection of Bech32 (Native SegWit) Bitcoin address starting with bc1q."""
        result = detector.detect(bitcoin_addresses["bech32"])

        assert result.detected is True
        assert result.coin_ticker == "BTC"
        assert result.coin_name == "Bitcoin"
        assert result.network == "mainnet"
        assert "Bech32" in result.address_type or "SegWit" in result.address_type
        assert result.confidence >= 0.98

    def test_detect_bech32m_taproot_address(self, detector, bitcoin_addresses):
        """Test detection of Bech32m (Taproot) Bitcoin address starting with bc1p."""
        result = detector.detect(bitcoin_addresses["bech32m"])

        assert result.detected is True
        assert result.coin_ticker == "BTC"
        assert result.coin_name == "Bitcoin"
        assert result.network == "mainnet"
        assert "Bech32m" in result.address_type or "Taproot" in result.address_type
        assert result.confidence >= 0.98

    def test_detect_testnet_address(self, detector, bitcoin_addresses):
        """Test detection of Bitcoin testnet address."""
        result = detector.detect(bitcoin_addresses["testnet"])

        assert result.detected is True
        assert result.coin_ticker == "BTC"
        assert result.network == "testnet"
        assert result.confidence >= 0.90

    def test_invalid_bitcoin_address_wrong_length(self, detector):
        """Test that truncated Bitcoin addresses are not detected as valid."""
        result = detector.detect("1BvBMSEYstWet")  # Too short

        # Should either not detect or have low confidence
        if result.detected and result.coin_ticker == "BTC":
            assert result.confidence < 0.9

    def test_invalid_bitcoin_address_bad_characters(self, detector):
        """Test that Bitcoin addresses with invalid characters are rejected."""
        # Bitcoin uses Base58 which excludes 0, O, I, l
        result = detector.detect("1BvBMSEYstWetOIl0xTFn5Au4m4GFg7xJaNVN2")

        # The regex should not match this
        assert result.coin_ticker != "BTC" or result.detected is False


# ==============================================================================
# Ethereum and EVM Address Tests
# ==============================================================================

class TestEthereumAddresses:
    """Tests for Ethereum and EVM-compatible address detection."""

    def test_detect_eth_address_lowercase(self, detector, ethereum_addresses):
        """Test detection of lowercase Ethereum address."""
        result = detector.detect(ethereum_addresses["lowercase"])

        assert result.detected is True
        assert result.coin_ticker == "ETH"
        assert result.coin_name == "Ethereum"
        assert result.address_type == "EVM Address"
        assert result.confidence >= 0.85
        assert "etherscan.io" in result.explorer_url

    def test_detect_eth_address_uppercase(self, detector, ethereum_addresses):
        """Test detection of uppercase Ethereum address."""
        result = detector.detect(ethereum_addresses["uppercase"])

        assert result.detected is True
        assert result.coin_ticker == "ETH"

    def test_detect_eth_address_mixed_case(self, detector, ethereum_addresses):
        """Test detection of mixed case (checksummed) Ethereum address."""
        result = detector.detect(ethereum_addresses["mixed"])

        assert result.detected is True
        assert result.coin_ticker == "ETH"

    def test_detect_evm_with_specific_chain(self, detector, ethereum_addresses):
        """Test EVM detection with specific chain specified."""
        address = ethereum_addresses["lowercase"]

        # Test Binance Smart Chain
        result = detector.detect_evm(address, "BNB")
        assert result.detected is True
        assert result.coin_ticker == "BNB"
        assert result.coin_name == "BNB Smart Chain"
        assert "bscscan.com" in result.explorer_url
        assert result.confidence >= 0.95

    def test_detect_evm_polygon(self, detector, ethereum_addresses):
        """Test EVM detection for Polygon."""
        result = detector.detect_evm(ethereum_addresses["lowercase"], "MATIC")

        assert result.detected is True
        assert result.coin_ticker == "MATIC"
        assert result.coin_name == "Polygon"
        assert "polygonscan.com" in result.explorer_url

    def test_detect_evm_arbitrum(self, detector, ethereum_addresses):
        """Test EVM detection for Arbitrum."""
        result = detector.detect_evm(ethereum_addresses["lowercase"], "ARB")

        assert result.detected is True
        assert result.coin_ticker == "ARB"
        assert result.coin_name == "Arbitrum"

    def test_detect_evm_unknown_chain_defaults_to_eth(self, detector, ethereum_addresses):
        """Test that unknown chain defaults to ETH."""
        result = detector.detect_evm(ethereum_addresses["lowercase"], "UNKNOWN")

        assert result.detected is True
        assert result.coin_ticker == "ETH"
        assert result.confidence == 0.85

    def test_detect_evm_invalid_address(self, detector):
        """Test that invalid address returns not detected."""
        result = detector.detect_evm("invalid_address", "ETH")

        assert result.detected is False

    def test_invalid_eth_address_wrong_prefix(self, detector):
        """Test that addresses without 0x prefix are not detected as ETH."""
        result = detector.detect("742d35cc6634c0532925a3b844bc9e7595f5ed0e")

        # Should not be detected as ETH (no 0x prefix)
        assert result.coin_ticker != "ETH" or result.detected is False or result.confidence < 0.85

    def test_invalid_eth_address_wrong_length(self, detector):
        """Test that ETH addresses with wrong length are rejected."""
        result = detector.detect("0x742d35cc6634c0532925a3b844bc9e7595f5")  # Too short

        assert result.coin_ticker != "ETH" or result.detected is False


# ==============================================================================
# Litecoin Address Tests
# ==============================================================================

class TestLitecoinAddresses:
    """Tests for Litecoin address detection."""

    def test_detect_ltc_p2pkh_legacy(self, detector, litecoin_addresses):
        """Test detection of P2PKH (Legacy) Litecoin address starting with L."""
        result = detector.detect(litecoin_addresses["p2pkh"])

        assert result.detected is True
        assert result.coin_ticker == "LTC"
        assert result.coin_name == "Litecoin"
        assert "P2PKH" in result.address_type or "Legacy" in result.address_type
        assert result.confidence >= 0.95

    def test_detect_ltc_p2sh_segwit(self, detector, litecoin_addresses):
        """Test detection of P2SH (SegWit) Litecoin address starting with M."""
        result = detector.detect(litecoin_addresses["p2sh"])

        assert result.detected is True
        assert result.coin_ticker == "LTC"
        assert "P2SH" in result.address_type or "SegWit" in result.address_type
        assert result.confidence >= 0.95

    def test_detect_ltc_bech32(self, detector, litecoin_addresses):
        """Test detection of Bech32 Litecoin address starting with ltc1."""
        result = detector.detect(litecoin_addresses["bech32"])

        assert result.detected is True
        assert result.coin_ticker == "LTC"
        assert "Bech32" in result.address_type
        assert result.confidence >= 0.98


# ==============================================================================
# Dogecoin Address Tests
# ==============================================================================

class TestDogecoinAddresses:
    """Tests for Dogecoin address detection."""

    def test_detect_doge_p2pkh(self, detector, dogecoin_addresses):
        """Test detection of P2PKH Dogecoin address starting with D."""
        result = detector.detect(dogecoin_addresses["p2pkh"])

        assert result.detected is True
        assert result.coin_ticker == "DOGE"
        assert result.coin_name == "Dogecoin"
        assert "P2PKH" in result.address_type
        assert result.confidence >= 0.95

    def test_detect_doge_p2sh(self, detector, dogecoin_addresses):
        """Test detection of P2SH Dogecoin address starting with A."""
        result = detector.detect(dogecoin_addresses["p2sh"])

        assert result.detected is True
        assert result.coin_ticker == "DOGE"
        assert "P2SH" in result.address_type
        assert result.confidence >= 0.90


# ==============================================================================
# XRP/Ripple Address Tests
# ==============================================================================

class TestXRPAddresses:
    """Tests for XRP/Ripple address detection."""

    def test_detect_xrp_classic_address(self, detector, xrp_addresses):
        """Test detection of classic XRP address starting with r."""
        result = detector.detect(xrp_addresses["classic"])

        assert result.detected is True
        assert result.coin_ticker == "XRP"
        assert result.coin_name == "Ripple"
        assert result.address_type == "Classic"
        assert result.confidence >= 0.95
        assert "xrpscan.com" in result.explorer_url

    def test_detect_xrp_x_address(self, detector, xrp_addresses):
        """Test detection of X-Address format XRP address."""
        result = detector.detect(xrp_addresses["x_address"])

        assert result.detected is True
        assert result.coin_ticker == "XRP"
        assert result.address_type == "X-Address"
        assert result.confidence >= 0.95


# ==============================================================================
# Cardano Address Tests
# ==============================================================================

class TestCardanoAddresses:
    """Tests for Cardano address detection."""

    def test_detect_cardano_shelley_address(self, detector, cardano_addresses):
        """Test detection of Shelley-era Cardano address."""
        result = detector.detect(cardano_addresses["shelley"])

        assert result.detected is True
        assert result.coin_ticker == "ADA"
        assert result.coin_name == "Cardano"
        assert result.address_type == "Shelley"
        assert result.confidence >= 0.98
        assert "cardanoscan.io" in result.explorer_url

    def test_detect_cardano_byron_icarus_address(self, detector, cardano_addresses):
        """Test detection of Byron (Icarus) Cardano address."""
        result = detector.detect(cardano_addresses["byron_icarus"])

        assert result.detected is True
        assert result.coin_ticker == "ADA"
        assert "Byron" in result.address_type or "Icarus" in result.address_type
        assert result.confidence >= 0.95

    def test_detect_cardano_byron_daedalus_address(self, detector, cardano_addresses):
        """Test detection of Byron (Daedalus) Cardano address."""
        result = detector.detect(cardano_addresses["byron_daedalus"])

        assert result.detected is True
        assert result.coin_ticker == "ADA"
        assert "Byron" in result.address_type or "Daedalus" in result.address_type
        assert result.confidence >= 0.95


# ==============================================================================
# Solana Address Tests
# ==============================================================================

class TestSolanaAddresses:
    """Tests for Solana address detection."""

    def test_detect_solana_address(self, detector, solana_addresses):
        """Test detection of Solana address."""
        result = detector.detect(solana_addresses["standard"])

        assert result.detected is True
        assert result.coin_ticker == "SOL"
        assert result.coin_name == "Solana"
        assert result.address_type == "Base58"
        assert result.confidence >= 0.70
        assert "solscan.io" in result.explorer_url

    def test_detect_solana_longer_address(self, detector, solana_addresses):
        """Test detection of longer Solana address."""
        result = detector.detect(solana_addresses["longer"])

        assert result.detected is True
        assert result.coin_ticker == "SOL"


# ==============================================================================
# Monero Address Tests
# ==============================================================================

class TestMoneroAddresses:
    """Tests for Monero address detection."""

    def test_detect_monero_standard_address(self, detector, monero_addresses):
        """Test detection of standard Monero address starting with 4."""
        result = detector.detect(monero_addresses["standard"])

        assert result.detected is True
        assert result.coin_ticker == "XMR"
        assert result.coin_name == "Monero"
        assert result.address_type == "Standard"
        assert result.confidence >= 0.98
        assert "xmrchain.net" in result.explorer_url

    def test_detect_monero_subaddress(self, detector, monero_addresses):
        """Test detection of Monero subaddress starting with 8."""
        result = detector.detect(monero_addresses["subaddress"])

        assert result.detected is True
        assert result.coin_ticker == "XMR"
        assert result.address_type == "Subaddress"
        assert result.confidence >= 0.98


# ==============================================================================
# Tron Address Tests
# ==============================================================================

class TestTronAddresses:
    """Tests for Tron address detection."""

    def test_detect_tron_address(self, detector, tron_addresses):
        """Test detection of Tron address starting with T."""
        result = detector.detect(tron_addresses["standard"])

        assert result.detected is True
        assert result.coin_ticker == "TRX"
        assert result.coin_name == "Tron"
        assert result.address_type == "Base58Check"
        assert result.confidence >= 0.95
        assert "tronscan.org" in result.explorer_url


# ==============================================================================
# Stellar Address Tests
# ==============================================================================

class TestStellarAddresses:
    """Tests for Stellar address detection."""

    def test_detect_stellar_address(self, detector, stellar_addresses):
        """Test detection of Stellar public key address starting with G."""
        result = detector.detect(stellar_addresses["standard"])

        assert result.detected is True
        assert result.coin_ticker == "XLM"
        assert result.coin_name == "Stellar"
        assert result.address_type == "Public Key"
        assert result.confidence >= 0.98
        assert "stellar.expert" in result.explorer_url


# ==============================================================================
# Other Cryptocurrency Tests
# ==============================================================================

class TestOtherCryptocurrencies:
    """Tests for other supported cryptocurrencies."""

    def test_detect_cosmos_address(self, detector):
        """Test detection of Cosmos (ATOM) address."""
        # Cosmos Bech32 addresses have exactly 38 characters after "cosmos1" (total 45 chars)
        address = "cosmos1yl6hdjhmkf37639730gffanpzndzdpmhwlkfhr"
        result = detector.detect(address)

        assert result.detected is True
        assert result.coin_ticker == "ATOM"
        assert result.coin_name == "Cosmos"

    def test_detect_tezos_address(self, detector):
        """Test detection of Tezos (XTZ) address."""
        address = "tz1VSUr8wwNhLAzempoch5d6hLRiTh8Cjcjb"
        result = detector.detect(address)

        assert result.detected is True
        assert result.coin_ticker == "XTZ"
        assert result.coin_name == "Tezos"

    def test_detect_zcash_transparent_address(self, detector):
        """Test detection of Zcash transparent address."""
        address = "t1Rv4exT7bqhZqi2j7xz8bUHDMxwosrjADU"
        result = detector.detect(address)

        assert result.detected is True
        assert result.coin_ticker == "ZEC"
        assert result.coin_name == "Zcash"

    def test_detect_dash_address(self, detector):
        """Test detection of Dash address."""
        address = "XrLj6XvkZMHqHsU7vPnRrfLZjBYPV5FJsP"
        result = detector.detect(address)

        assert result.detected is True
        assert result.coin_ticker == "DASH"
        assert result.coin_name == "Dash"

    def test_detect_hedera_address(self, detector):
        """Test detection of Hedera (HBAR) account ID."""
        address = "0.0.123456"
        result = detector.detect(address)

        assert result.detected is True
        assert result.coin_ticker == "HBAR"
        assert result.coin_name == "Hedera"

    def test_detect_near_named_account(self, detector):
        """Test detection of NEAR Protocol named account."""
        address = "alice.near"
        result = detector.detect(address)

        assert result.detected is True
        assert result.coin_ticker == "NEAR"
        assert result.coin_name == "NEAR Protocol"

    def test_detect_filecoin_address(self, detector):
        """Test detection of Filecoin address."""
        address = "f1abjxfbp274xpdqcpuaykwkfb43omjotacm2p3za"
        result = detector.detect(address)

        assert result.detected is True
        assert result.coin_ticker == "FIL"
        assert result.coin_name == "Filecoin"


# ==============================================================================
# Invalid/Malformed Address Tests
# ==============================================================================

class TestInvalidAddresses:
    """Tests for invalid and malformed addresses."""

    def test_empty_string_not_detected(self, detector):
        """Test that empty string is not detected as any cryptocurrency."""
        result = detector.detect("")

        assert result.detected is False
        assert result.coin_ticker is None
        assert result.coin_name is None

    def test_none_not_detected(self, detector):
        """Test that None is not detected as any cryptocurrency."""
        result = detector.detect(None)

        assert result.detected is False
        assert result.address == ""

    def test_whitespace_only_not_detected(self, detector):
        """Test that whitespace-only strings are not detected."""
        result = detector.detect("   \t\n   ")

        assert result.detected is False

    def test_random_string_not_detected(self, detector):
        """Test that random strings are not detected."""
        result = detector.detect("hello world this is not an address")

        assert result.detected is False

    def test_partial_address_not_high_confidence(self, detector):
        """Test that partial/truncated addresses don't have high confidence."""
        result = detector.detect("1BvBMSE")  # Too short for Bitcoin

        # Either not detected, or if detected, should be low confidence
        if result.detected:
            assert result.confidence < 0.95

    def test_special_characters_not_detected(self, detector):
        """Test that addresses with special characters are not detected."""
        result = detector.detect("!@#$%^&*()_+{}|:<>?")

        assert result.detected is False

    def test_sql_injection_not_detected(self, detector):
        """Test that SQL injection attempts are not detected as addresses."""
        result = detector.detect("'; DROP TABLE addresses; --")

        assert result.detected is False

    def test_numeric_only_not_high_confidence(self, detector):
        """Test that numeric-only strings don't return high confidence."""
        result = detector.detect("12345678901234567890")

        # May match some patterns, but should not be high confidence
        if result.detected and result.coin_ticker in ["BTC", "ETH"]:
            assert result.confidence < 0.95

    def test_unicode_characters_handled(self, detector):
        """Test that Unicode characters are handled gracefully."""
        result = detector.detect("bitcoin_address_with_unicode")

        assert result.detected is False

    def test_very_long_string_handled(self, detector):
        """Test that very long strings are handled without crashing."""
        long_string = "a" * 10000
        result = detector.detect(long_string)

        # Should complete without exception
        assert isinstance(result, CryptoDetectionResult)


# ==============================================================================
# Edge Cases Tests
# ==============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_address_with_leading_whitespace(self, detector, bitcoin_addresses):
        """Test that addresses with leading whitespace are still detected."""
        result = detector.detect("   " + bitcoin_addresses["bech32"])

        assert result.detected is True
        assert result.coin_ticker == "BTC"

    def test_address_with_trailing_whitespace(self, detector, bitcoin_addresses):
        """Test that addresses with trailing whitespace are still detected."""
        result = detector.detect(bitcoin_addresses["bech32"] + "   ")

        assert result.detected is True
        assert result.coin_ticker == "BTC"

    def test_address_with_surrounding_whitespace(self, detector, ethereum_addresses):
        """Test that addresses with surrounding whitespace are still detected."""
        result = detector.detect("  " + ethereum_addresses["lowercase"] + "  ")

        assert result.detected is True
        assert result.coin_ticker == "ETH"

    def test_address_minimum_length_boundary(self, detector):
        """Test addresses at minimum length boundaries."""
        # Very short addresses that might match patterns
        result = detector.detect("1a")

        # Should not match Bitcoin P2PKH (min 26 chars)
        if result.detected and result.coin_ticker == "BTC":
            assert False, "Should not detect 2-char string as Bitcoin"

    def test_address_maximum_length_boundary(self, detector):
        """Test addresses at maximum length boundaries."""
        # Bitcoin P2PKH max is about 35 characters
        long_btc = "1" + "a" * 40
        result = detector.detect(long_btc)

        # Should not match if too long
        if result.detected and result.coin_ticker == "BTC":
            assert result.address_type != "P2PKH (Legacy)"

    def test_case_sensitivity_bitcoin(self, detector):
        """Test that Bitcoin Bech32 addresses are case-sensitive (lowercase only)."""
        bech32_upper = "BC1QAR0SRRR7XFKVY5L643LYDNW9RE59GTZZWF5MDQ"
        result = detector.detect(bech32_upper)

        # Bech32 should only match lowercase
        if result.detected and result.coin_ticker == "BTC":
            assert "Bech32" not in result.address_type

    def test_integer_input_handled(self, detector):
        """Test that non-string input is handled gracefully."""
        result = detector.detect(12345)

        assert result.detected is False

    def test_list_input_handled(self, detector):
        """Test that list input is handled gracefully."""
        result = detector.detect(["address1", "address2"])

        assert result.detected is False


# ==============================================================================
# detect_all_possible Function Tests
# ==============================================================================

class TestDetectAllPossible:
    """Tests for the detect_all_possible function."""

    def test_evm_address_returns_multiple_chains(self, detector, ethereum_addresses):
        """Test that EVM address returns multiple possible chains."""
        results = detector.detect_all_possible(ethereum_addresses["lowercase"])

        assert len(results) > 1

        # Check that ETH is in results
        eth_results = [r for r in results if r.coin_ticker == "ETH"]
        assert len(eth_results) >= 1

        # Check that other EVM chains are included
        tickers = {r.coin_ticker for r in results}
        assert "ETH" in tickers
        # Should include some other EVM chains
        assert len(tickers) > 1

    def test_results_sorted_by_confidence(self, detector, ethereum_addresses):
        """Test that results are sorted by confidence (highest first)."""
        results = detector.detect_all_possible(ethereum_addresses["lowercase"])

        confidences = [r.confidence for r in results]
        assert confidences == sorted(confidences, reverse=True)

    def test_specific_address_returns_single_match(self, detector, bitcoin_addresses):
        """Test that specific addresses return fewer matches."""
        results = detector.detect_all_possible(bitcoin_addresses["bech32"])

        # Bitcoin Bech32 is very specific
        btc_results = [r for r in results if r.coin_ticker == "BTC"]
        assert len(btc_results) >= 1
        assert btc_results[0].confidence >= 0.98

    def test_empty_address_returns_empty_list(self, detector):
        """Test that empty address returns empty list."""
        results = detector.detect_all_possible("")

        assert results == []

    def test_all_results_are_detection_results(self, detector, ethereum_addresses):
        """Test that all results are CryptoDetectionResult instances."""
        results = detector.detect_all_possible(ethereum_addresses["lowercase"])

        for result in results:
            assert isinstance(result, CryptoDetectionResult)
            assert result.detected is True

    def test_all_results_have_explorer_urls(self, detector, ethereum_addresses):
        """Test that all results have explorer URLs."""
        results = detector.detect_all_possible(ethereum_addresses["lowercase"])

        for result in results:
            assert result.explorer_url is not None
            assert result.explorer_url.startswith("http")


# ==============================================================================
# get_supported_cryptocurrencies Function Tests
# ==============================================================================

class TestGetSupportedCryptocurrencies:
    """Tests for the get_supported_cryptocurrencies function."""

    def test_returns_list(self, detector):
        """Test that function returns a list."""
        result = detector.get_supported_cryptocurrencies()

        assert isinstance(result, list)

    def test_returns_non_empty_list(self, detector):
        """Test that the list is not empty."""
        result = detector.get_supported_cryptocurrencies()

        assert len(result) > 0

    def test_each_item_has_required_fields(self, detector):
        """Test that each item has coin_name and coin_ticker."""
        result = detector.get_supported_cryptocurrencies()

        for item in result:
            assert "coin_name" in item
            assert "coin_ticker" in item
            assert isinstance(item["coin_name"], str)
            assert isinstance(item["coin_ticker"], str)

    def test_includes_major_cryptocurrencies(self, detector):
        """Test that major cryptocurrencies are included."""
        result = detector.get_supported_cryptocurrencies()
        tickers = {item["coin_ticker"] for item in result}

        # Check for major cryptocurrencies
        assert "BTC" in tickers
        assert "ETH" in tickers
        assert "LTC" in tickers
        assert "XRP" in tickers
        assert "ADA" in tickers
        assert "SOL" in tickers
        assert "DOGE" in tickers

    def test_includes_evm_chains(self, detector):
        """Test that EVM chains are included."""
        result = detector.get_supported_cryptocurrencies()
        tickers = {item["coin_ticker"] for item in result}

        # Check for EVM chains
        assert "BNB" in tickers or "MATIC" in tickers

    def test_no_duplicate_tickers(self, detector):
        """Test that there are no duplicate tickers."""
        result = detector.get_supported_cryptocurrencies()
        tickers = [item["coin_ticker"] for item in result]

        assert len(tickers) == len(set(tickers))

    def test_sorted_by_coin_name(self, detector):
        """Test that results are sorted by coin_name."""
        result = detector.get_supported_cryptocurrencies()
        names = [item["coin_name"] for item in result]

        assert names == sorted(names)


# ==============================================================================
# Convenience Functions Tests
# ==============================================================================

class TestConvenienceFunctions:
    """Tests for the module-level convenience functions."""

    def test_detect_crypto_address_function(self, bitcoin_addresses):
        """Test the detect_crypto_address convenience function."""
        result = detect_crypto_address(bitcoin_addresses["bech32"])

        assert isinstance(result, CryptoDetectionResult)
        assert result.detected is True
        assert result.coin_ticker == "BTC"

    def test_detect_all_crypto_addresses_function(self, ethereum_addresses):
        """Test the detect_all_crypto_addresses convenience function."""
        results = detect_all_crypto_addresses(ethereum_addresses["lowercase"])

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, CryptoDetectionResult) for r in results)


# ==============================================================================
# CryptoDetectionResult Tests
# ==============================================================================

class TestCryptoDetectionResult:
    """Tests for the CryptoDetectionResult dataclass."""

    def test_to_dict_method(self, detector, bitcoin_addresses):
        """Test the to_dict method returns proper dictionary."""
        result = detector.detect(bitcoin_addresses["bech32"])
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "address" in result_dict
        assert "detected" in result_dict
        assert "coin_name" in result_dict
        assert "coin_ticker" in result_dict
        assert "network" in result_dict
        assert "address_type" in result_dict
        assert "confidence" in result_dict
        assert "explorer_url" in result_dict

    def test_to_dict_values_match(self, detector, bitcoin_addresses):
        """Test that to_dict values match the result attributes."""
        result = detector.detect(bitcoin_addresses["bech32"])
        result_dict = result.to_dict()

        assert result_dict["address"] == result.address
        assert result_dict["detected"] == result.detected
        assert result_dict["coin_name"] == result.coin_name
        assert result_dict["coin_ticker"] == result.coin_ticker
        assert result_dict["confidence"] == result.confidence

    def test_undetected_result_to_dict(self, detector):
        """Test to_dict for undetected result."""
        result = detector.detect("invalid_address")
        result_dict = result.to_dict()

        assert result_dict["detected"] is False
        assert result_dict["coin_name"] is None
        assert result_dict["coin_ticker"] is None


# ==============================================================================
# Confidence Level Tests
# ==============================================================================

class TestConfidenceLevels:
    """Tests to verify confidence levels are appropriate."""

    def test_high_confidence_for_unique_formats(self, detector):
        """Test that unique address formats have high confidence."""
        # Bech32 Bitcoin addresses are very specific
        result = detector.detect("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")
        assert result.confidence >= 0.98

    def test_medium_confidence_for_shared_formats(self, detector, ethereum_addresses):
        """Test that shared formats (like 0x) have medium confidence."""
        result = detector.detect(ethereum_addresses["lowercase"])

        # EVM addresses could be multiple chains
        assert 0.80 <= result.confidence <= 0.95

    def test_lower_confidence_for_ambiguous_formats(self, detector, solana_addresses):
        """Test that ambiguous formats have lower confidence."""
        result = detector.detect(solana_addresses["standard"])

        # Solana Base58 could match other patterns
        assert result.confidence <= 0.90


# ==============================================================================
# Explorer URL Tests
# ==============================================================================

class TestExplorerURLs:
    """Tests for explorer URL generation."""

    def test_explorer_url_contains_address(self, detector, bitcoin_addresses):
        """Test that explorer URL contains the address."""
        address = bitcoin_addresses["bech32"]
        result = detector.detect(address)

        assert address in result.explorer_url

    def test_different_chains_different_explorers(self, detector):
        """Test that different chains have different explorer URLs."""
        btc_result = detector.detect("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")
        eth_result = detector.detect("0x742d35cc6634c0532925a3b844bc9e7595f5ed0e")

        assert "blockchain.com" in btc_result.explorer_url
        assert "etherscan.io" in eth_result.explorer_url

    def test_explorer_url_is_valid_format(self, detector, bitcoin_addresses):
        """Test that explorer URLs are valid HTTP(S) URLs."""
        result = detector.detect(bitcoin_addresses["bech32"])

        assert result.explorer_url.startswith("http://") or result.explorer_url.startswith("https://")


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestIntegration:
    """Integration tests combining multiple features."""

    def test_detect_and_serialize_workflow(self, detector, bitcoin_addresses):
        """Test typical workflow of detecting and serializing result."""
        # Detect
        result = detector.detect(bitcoin_addresses["bech32"])

        # Serialize
        data = result.to_dict()

        # Verify serialization
        assert data["detected"] is True
        assert data["coin_ticker"] == "BTC"

        # Could be sent as JSON
        import json
        json_str = json.dumps(data)
        assert isinstance(json_str, str)

        # Could be deserialized
        restored = json.loads(json_str)
        assert restored["coin_ticker"] == "BTC"

    def test_batch_detection(self, detector):
        """Test detecting multiple addresses in sequence."""
        addresses = [
            ("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", "BTC"),
            ("0x742d35cc6634c0532925a3b844bc9e7595f5ed0e", "ETH"),
            ("LM2WMpR1Rp6j3Sa59cMXMs1SPzj9eXpGc1", "LTC"),
            ("D7Y55bkvqN29LYLxRq6Qjx5N7yx2cN4fY5", "DOGE"),
        ]

        for address, expected_ticker in addresses:
            result = detector.detect(address)
            assert result.detected is True
            assert result.coin_ticker == expected_ticker

    def test_detector_instance_reuse(self, detector):
        """Test that detector instance can be reused multiple times."""
        # First detection
        result1 = detector.detect("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")

        # Second detection
        result2 = detector.detect("0x742d35cc6634c0532925a3b844bc9e7595f5ed0e")

        # Third detection (same as first)
        result3 = detector.detect("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")

        assert result1.coin_ticker == "BTC"
        assert result2.coin_ticker == "ETH"
        assert result3.coin_ticker == "BTC"
        assert result1.address == result3.address
