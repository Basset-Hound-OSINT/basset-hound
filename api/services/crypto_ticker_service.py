"""
Crypto Ticker Service for Basset Hound

Provides enhanced cryptocurrency ticker information for wallet addresses,
building on top of the existing crypto_detector utility to add display
metadata, block explorer URLs, and frontend-friendly formatting.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from api.utils.crypto_detector import (
    CryptoAddressDetector,
    CryptoDetectionResult,
    detect_crypto_address,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Block Explorer Configuration
# =============================================================================

BLOCK_EXPLORERS: Dict[str, Dict[str, str]] = {
    "bitcoin": {
        "mainnet": "https://blockchair.com/bitcoin/address/{address}",
        "testnet": "https://blockstream.info/testnet/address/{address}",
    },
    "ethereum": {
        "mainnet": "https://etherscan.io/address/{address}",
        "goerli": "https://goerli.etherscan.io/address/{address}",
        "sepolia": "https://sepolia.etherscan.io/address/{address}",
    },
    "litecoin": {
        "mainnet": "https://blockchair.com/litecoin/address/{address}",
    },
    "dogecoin": {
        "mainnet": "https://dogechain.info/address/{address}",
    },
    "bitcoin_cash": {
        "mainnet": "https://blockchair.com/bitcoin-cash/address/{address}",
    },
    "ripple": {
        "mainnet": "https://xrpscan.com/account/{address}",
    },
    "cardano": {
        "mainnet": "https://cardanoscan.io/address/{address}",
    },
    "solana": {
        "mainnet": "https://solscan.io/account/{address}",
        "devnet": "https://solscan.io/account/{address}?cluster=devnet",
    },
    "polkadot": {
        "mainnet": "https://polkascan.io/polkadot/account/{address}",
    },
    "cosmos": {
        "mainnet": "https://atomscan.com/accounts/{address}",
    },
    "tron": {
        "mainnet": "https://tronscan.org/#/address/{address}",
    },
    "stellar": {
        "mainnet": "https://stellar.expert/explorer/public/account/{address}",
    },
    "monero": {
        "mainnet": "https://xmrchain.net/search?value={address}",
    },
    "avalanche": {
        "mainnet": "https://snowtrace.io/address/{address}",
        "x-chain": "https://avascan.info/blockchain/x/address/{address}",
        "p-chain": "https://avascan.info/blockchain/p/address/{address}",
        "c-chain": "https://snowtrace.io/address/{address}",
    },
    "bnb_smart_chain": {
        "mainnet": "https://bscscan.com/address/{address}",
    },
    "polygon": {
        "mainnet": "https://polygonscan.com/address/{address}",
    },
    "arbitrum": {
        "mainnet": "https://arbiscan.io/address/{address}",
    },
    "optimism": {
        "mainnet": "https://optimistic.etherscan.io/address/{address}",
    },
    "fantom": {
        "mainnet": "https://ftmscan.com/address/{address}",
    },
    "zcash": {
        "mainnet": "https://zcashblockexplorer.com/address/{address}",
    },
    "dash": {
        "mainnet": "https://blockchair.com/dash/address/{address}",
    },
    "tezos": {
        "mainnet": "https://tzkt.io/{address}",
    },
    "hedera": {
        "mainnet": "https://hashscan.io/mainnet/account/{address}",
    },
    "near": {
        "mainnet": "https://explorer.near.org/accounts/{address}",
    },
    "algorand": {
        "mainnet": "https://algoexplorer.io/address/{address}",
    },
    "filecoin": {
        "mainnet": "https://filfox.info/en/address/{address}",
    },
    "aptos": {
        "mainnet": "https://explorer.aptoslabs.com/account/{address}",
    },
    "sui": {
        "mainnet": "https://suiexplorer.com/address/{address}",
    },
    "eos": {
        "mainnet": "https://bloks.io/account/{address}",
    },
    "neo": {
        "mainnet": "https://neoscan.io/address/{address}",
        "neo3": "https://neo3.neotube.io/address/{address}",
    },
    "base": {
        "mainnet": "https://basescan.org/address/{address}",
    },
    "cronos": {
        "mainnet": "https://cronoscan.com/address/{address}",
    },
    "gnosis": {
        "mainnet": "https://gnosisscan.io/address/{address}",
    },
    "celo": {
        "mainnet": "https://celoscan.io/address/{address}",
    },
}


# =============================================================================
# Currency Display Metadata
# =============================================================================

CURRENCY_METADATA: Dict[str, Dict[str, str]] = {
    "BTC": {
        "display_name": "Bitcoin",
        "icon_class": "fab fa-bitcoin",
        "currency_key": "bitcoin",
    },
    "ETH": {
        "display_name": "Ethereum",
        "icon_class": "fab fa-ethereum",
        "currency_key": "ethereum",
    },
    "LTC": {
        "display_name": "Litecoin",
        "icon_class": "fas fa-coins",
        "currency_key": "litecoin",
    },
    "DOGE": {
        "display_name": "Dogecoin",
        "icon_class": "fas fa-dog",
        "currency_key": "dogecoin",
    },
    "BCH": {
        "display_name": "Bitcoin Cash",
        "icon_class": "fab fa-bitcoin",
        "currency_key": "bitcoin_cash",
    },
    "XRP": {
        "display_name": "Ripple",
        "icon_class": "fas fa-water",
        "currency_key": "ripple",
    },
    "ADA": {
        "display_name": "Cardano",
        "icon_class": "fas fa-circle-nodes",
        "currency_key": "cardano",
    },
    "SOL": {
        "display_name": "Solana",
        "icon_class": "fas fa-sun",
        "currency_key": "solana",
    },
    "DOT": {
        "display_name": "Polkadot",
        "icon_class": "fas fa-circle-dot",
        "currency_key": "polkadot",
    },
    "ATOM": {
        "display_name": "Cosmos",
        "icon_class": "fas fa-atom",
        "currency_key": "cosmos",
    },
    "TRX": {
        "display_name": "Tron",
        "icon_class": "fas fa-bolt",
        "currency_key": "tron",
    },
    "XLM": {
        "display_name": "Stellar",
        "icon_class": "fas fa-star",
        "currency_key": "stellar",
    },
    "XMR": {
        "display_name": "Monero",
        "icon_class": "fas fa-user-secret",
        "currency_key": "monero",
    },
    "AVAX": {
        "display_name": "Avalanche",
        "icon_class": "fas fa-mountain",
        "currency_key": "avalanche",
    },
    "BNB": {
        "display_name": "BNB Smart Chain",
        "icon_class": "fas fa-coins",
        "currency_key": "bnb_smart_chain",
    },
    "MATIC": {
        "display_name": "Polygon",
        "icon_class": "fas fa-hexagon",
        "currency_key": "polygon",
    },
    "ARB": {
        "display_name": "Arbitrum",
        "icon_class": "fas fa-layer-group",
        "currency_key": "arbitrum",
    },
    "OP": {
        "display_name": "Optimism",
        "icon_class": "fas fa-circle-up",
        "currency_key": "optimism",
    },
    "FTM": {
        "display_name": "Fantom",
        "icon_class": "fas fa-ghost",
        "currency_key": "fantom",
    },
    "ZEC": {
        "display_name": "Zcash",
        "icon_class": "fas fa-shield-halved",
        "currency_key": "zcash",
    },
    "DASH": {
        "display_name": "Dash",
        "icon_class": "fas fa-bolt-lightning",
        "currency_key": "dash",
    },
    "XTZ": {
        "display_name": "Tezos",
        "icon_class": "fas fa-bread-slice",
        "currency_key": "tezos",
    },
    "HBAR": {
        "display_name": "Hedera",
        "icon_class": "fas fa-hashtag",
        "currency_key": "hedera",
    },
    "NEAR": {
        "display_name": "NEAR Protocol",
        "icon_class": "fas fa-globe",
        "currency_key": "near",
    },
    "ALGO": {
        "display_name": "Algorand",
        "icon_class": "fas fa-a",
        "currency_key": "algorand",
    },
    "FIL": {
        "display_name": "Filecoin",
        "icon_class": "fas fa-file",
        "currency_key": "filecoin",
    },
    "APT": {
        "display_name": "Aptos",
        "icon_class": "fas fa-cube",
        "currency_key": "aptos",
    },
    "SUI": {
        "display_name": "Sui",
        "icon_class": "fas fa-droplet",
        "currency_key": "sui",
    },
    "EOS": {
        "display_name": "EOS",
        "icon_class": "fas fa-infinity",
        "currency_key": "eos",
    },
    "NEO": {
        "display_name": "NEO",
        "icon_class": "fas fa-n",
        "currency_key": "neo",
    },
    "BASE": {
        "display_name": "Base",
        "icon_class": "fas fa-square",
        "currency_key": "base",
    },
    "CRONOS": {
        "display_name": "Cronos",
        "icon_class": "fas fa-clock",
        "currency_key": "cronos",
    },
    "GNOSIS": {
        "display_name": "Gnosis Chain",
        "icon_class": "fas fa-owl",
        "currency_key": "gnosis",
    },
    "CELO": {
        "display_name": "Celo",
        "icon_class": "fas fa-mobile-screen",
        "currency_key": "celo",
    },
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class CryptoTickerInfo:
    """
    Comprehensive ticker information for a cryptocurrency address.

    Attributes:
        address: The cryptocurrency wallet address
        currency: Currency ticker symbol (BTC, ETH, LTC, etc.)
        network: Network type (mainnet, testnet, etc.)
        ticker_symbol: Trading ticker symbol
        display_name: Human-readable currency name (Bitcoin, Ethereum, etc.)
        icon_class: FontAwesome icon class for frontend display
        explorer_url: Link to block explorer for the address
        is_valid: Whether the address is valid for the detected currency
        address_type: Type of address (P2PKH, Bech32, EVM, etc.)
        confidence: Detection confidence score (0.0 to 1.0)
    """
    address: str
    currency: str
    network: str
    ticker_symbol: str
    display_name: str
    icon_class: str
    explorer_url: Optional[str] = None
    is_valid: bool = True
    address_type: Optional[str] = None
    confidence: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "address": self.address,
            "currency": self.currency,
            "network": self.network,
            "ticker_symbol": self.ticker_symbol,
            "display_name": self.display_name,
            "icon_class": self.icon_class,
            "explorer_url": self.explorer_url,
            "is_valid": self.is_valid,
            "address_type": self.address_type,
            "confidence": self.confidence,
        }


# =============================================================================
# Crypto Ticker Service
# =============================================================================

class CryptoTickerService:
    """
    Service for retrieving cryptocurrency ticker information.

    Builds on the CryptoAddressDetector to provide enhanced display
    information including icons, explorer URLs, and frontend metadata.

    Usage:
        service = CryptoTickerService()
        info = service.get_ticker_info("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")
        print(info.display_name)  # "Bitcoin"
        print(info.icon_class)    # "fab fa-bitcoin"
    """

    def __init__(self):
        """Initialize the ticker service with a crypto detector."""
        self._detector = CryptoAddressDetector()

    def get_ticker_info(self, address: str) -> Optional[CryptoTickerInfo]:
        """
        Get comprehensive ticker information for a cryptocurrency address.

        Args:
            address: The cryptocurrency wallet address to analyze

        Returns:
            CryptoTickerInfo with full ticker details, or None if not detected
        """
        if not address or not isinstance(address, str):
            return None

        address = address.strip()
        if not address:
            return None

        # Use the detector to identify the cryptocurrency
        result = self._detector.detect(address)

        if not result.detected:
            return None

        return self._build_ticker_info(result)

    def get_ticker_info_batch(
        self, addresses: List[str]
    ) -> Dict[str, CryptoTickerInfo]:
        """
        Get ticker information for multiple addresses.

        Args:
            addresses: List of cryptocurrency wallet addresses

        Returns:
            Dictionary mapping addresses to their CryptoTickerInfo
        """
        results: Dict[str, CryptoTickerInfo] = {}

        for address in addresses:
            if not address or not isinstance(address, str):
                continue

            address = address.strip()
            if not address:
                continue

            info = self.get_ticker_info(address)
            if info:
                results[address] = info

        return results

    def get_supported_currencies(self) -> List[dict]:
        """
        Get list of all supported cryptocurrencies with metadata.

        Returns:
            List of dictionaries containing currency information:
            - ticker_symbol: Currency ticker (BTC, ETH, etc.)
            - display_name: Human-readable name
            - icon_class: FontAwesome icon class
            - has_explorer: Whether a block explorer is configured
        """
        supported = self._detector.get_supported_cryptocurrencies()
        result = []

        for crypto in supported:
            ticker = crypto["coin_ticker"]
            metadata = CURRENCY_METADATA.get(ticker, {})
            currency_key = metadata.get("currency_key", ticker.lower())

            result.append({
                "ticker_symbol": ticker,
                "display_name": metadata.get("display_name", crypto["coin_name"]),
                "icon_class": metadata.get("icon_class", "fas fa-coins"),
                "has_explorer": currency_key in BLOCK_EXPLORERS,
            })

        return result

    def format_explorer_url(
        self, address: str, currency: str, network: str = "mainnet"
    ) -> str:
        """
        Generate a block explorer URL for an address.

        Args:
            address: The cryptocurrency wallet address
            currency: Currency ticker symbol (BTC, ETH, etc.)
            network: Network type (mainnet, testnet, etc.)

        Returns:
            Block explorer URL string, or empty string if not available
        """
        metadata = CURRENCY_METADATA.get(currency.upper(), {})
        currency_key = metadata.get("currency_key", currency.lower())

        explorer_config = BLOCK_EXPLORERS.get(currency_key, {})
        network_lower = network.lower()

        # Try exact network match first
        if network_lower in explorer_config:
            return explorer_config[network_lower].format(address=address)

        # Fallback to mainnet
        if "mainnet" in explorer_config:
            return explorer_config["mainnet"].format(address=address)

        # Return empty if no explorer configured
        return ""

    def _build_ticker_info(self, result: CryptoDetectionResult) -> CryptoTickerInfo:
        """
        Build a CryptoTickerInfo from a detection result.

        Args:
            result: CryptoDetectionResult from the detector

        Returns:
            CryptoTickerInfo with full ticker information
        """
        ticker = result.coin_ticker or ""
        metadata = CURRENCY_METADATA.get(ticker, {})

        # Get explorer URL
        explorer_url = result.explorer_url
        if not explorer_url and ticker:
            explorer_url = self.format_explorer_url(
                result.address,
                ticker,
                result.network or "mainnet"
            )

        return CryptoTickerInfo(
            address=result.address,
            currency=ticker,
            network=result.network or "mainnet",
            ticker_symbol=ticker,
            display_name=metadata.get("display_name", result.coin_name or ticker),
            icon_class=metadata.get("icon_class", "fas fa-coins"),
            explorer_url=explorer_url or None,
            is_valid=result.detected,
            address_type=result.address_type,
            confidence=result.confidence,
        )


# =============================================================================
# Singleton Instance
# =============================================================================

_ticker_service: Optional[CryptoTickerService] = None


def get_crypto_ticker_service() -> CryptoTickerService:
    """
    Get or create the crypto ticker service singleton.

    Returns:
        CryptoTickerService instance
    """
    global _ticker_service

    if _ticker_service is None:
        _ticker_service = CryptoTickerService()

    return _ticker_service


def set_crypto_ticker_service(service: Optional[CryptoTickerService]) -> None:
    """Set the ticker service singleton (for testing)."""
    global _ticker_service
    _ticker_service = service
