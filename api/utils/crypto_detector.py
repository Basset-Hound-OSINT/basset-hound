"""
Cryptocurrency Address Detection Utility

Automatically detects cryptocurrency type from wallet address format.
Supports 20+ major cryptocurrencies with comprehensive pattern matching.
"""

import re
import hashlib
from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class CryptoDetectionResult:
    """Result of cryptocurrency address detection."""
    address: str
    detected: bool
    coin_name: Optional[str] = None
    coin_ticker: Optional[str] = None
    network: Optional[str] = None
    address_type: Optional[str] = None
    confidence: float = 0.0
    explorer_url: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "address": self.address,
            "detected": self.detected,
            "coin_name": self.coin_name,
            "coin_ticker": self.coin_ticker,
            "network": self.network,
            "address_type": self.address_type,
            "confidence": self.confidence,
            "explorer_url": self.explorer_url,
        }


class CryptoAddressDetector:
    """
    Detects cryptocurrency type from wallet address format.

    Usage:
        detector = CryptoAddressDetector()
        result = detector.detect("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")
        print(result.coin_ticker)  # "BTC"
    """

    # Address patterns with (regex, coin_name, ticker, network, address_type, confidence, explorer_template)
    PATTERNS: List[Tuple[str, str, str, str, str, float, str]] = [
        # Bitcoin (BTC)
        (r"^1[a-km-zA-HJ-NP-Z1-9]{25,34}$", "Bitcoin", "BTC", "mainnet", "P2PKH (Legacy)", 0.95,
         "https://blockchain.com/btc/address/{address}"),
        (r"^3[a-km-zA-HJ-NP-Z1-9]{25,34}$", "Bitcoin", "BTC", "mainnet", "P2SH (SegWit Compatible)", 0.95,
         "https://blockchain.com/btc/address/{address}"),
        (r"^bc1q[a-z0-9]{38,58}$", "Bitcoin", "BTC", "mainnet", "Bech32 (Native SegWit)", 0.98,
         "https://blockchain.com/btc/address/{address}"),
        (r"^bc1p[a-z0-9]{58}$", "Bitcoin", "BTC", "mainnet", "Bech32m (Taproot)", 0.98,
         "https://blockchain.com/btc/address/{address}"),
        (r"^(tb1|bcrt1)[a-z0-9]{38,58}$", "Bitcoin", "BTC", "testnet", "Testnet", 0.90,
         "https://blockstream.info/testnet/address/{address}"),

        # Ethereum and EVM-compatible (ETH, BNB, MATIC, AVAX, etc.)
        (r"^0x[a-fA-F0-9]{40}$", "Ethereum", "ETH", "mainnet", "EVM Address", 0.85,
         "https://etherscan.io/address/{address}"),

        # Litecoin (LTC)
        (r"^L[a-km-zA-HJ-NP-Z1-9]{26,33}$", "Litecoin", "LTC", "mainnet", "P2PKH (Legacy)", 0.95,
         "https://blockchair.com/litecoin/address/{address}"),
        (r"^M[a-km-zA-HJ-NP-Z1-9]{26,33}$", "Litecoin", "LTC", "mainnet", "P2SH (SegWit)", 0.95,
         "https://blockchair.com/litecoin/address/{address}"),
        (r"^ltc1q[a-z0-9]{38,58}$", "Litecoin", "LTC", "mainnet", "Bech32 (Native SegWit)", 0.98,
         "https://blockchair.com/litecoin/address/{address}"),

        # Dogecoin (DOGE)
        (r"^D[5-9A-HJ-NP-U][a-km-zA-HJ-NP-Z1-9]{24,32}$", "Dogecoin", "DOGE", "mainnet", "P2PKH", 0.95,
         "https://dogechain.info/address/{address}"),
        (r"^A[a-km-zA-HJ-NP-Z1-9]{25,34}$", "Dogecoin", "DOGE", "mainnet", "P2SH", 0.90,
         "https://dogechain.info/address/{address}"),

        # Bitcoin Cash (BCH)
        (r"^bitcoincash:q[a-z0-9]{41}$", "Bitcoin Cash", "BCH", "mainnet", "CashAddr", 0.98,
         "https://blockchair.com/bitcoin-cash/address/{address}"),
        (r"^q[a-z0-9]{41}$", "Bitcoin Cash", "BCH", "mainnet", "CashAddr (no prefix)", 0.85,
         "https://blockchair.com/bitcoin-cash/address/{address}"),
        (r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$", "Bitcoin Cash", "BCH", "mainnet", "Legacy (shared with BTC)", 0.50,
         "https://blockchair.com/bitcoin-cash/address/{address}"),

        # Ripple/XRP
        (r"^r[0-9a-zA-Z]{24,34}$", "Ripple", "XRP", "mainnet", "Classic", 0.95,
         "https://xrpscan.com/account/{address}"),
        (r"^X[0-9a-zA-Z]{46}$", "Ripple", "XRP", "mainnet", "X-Address", 0.95,
         "https://xrpscan.com/account/{address}"),

        # Cardano (ADA)
        (r"^addr1[a-z0-9]{53,}$", "Cardano", "ADA", "mainnet", "Shelley", 0.98,
         "https://cardanoscan.io/address/{address}"),
        (r"^Ae2[a-zA-Z0-9]{50,}$", "Cardano", "ADA", "mainnet", "Byron (Icarus)", 0.95,
         "https://cardanoscan.io/address/{address}"),
        (r"^DdzFF[a-zA-Z0-9]{50,}$", "Cardano", "ADA", "mainnet", "Byron (Daedalus)", 0.95,
         "https://cardanoscan.io/address/{address}"),

        # Solana (SOL)
        (r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", "Solana", "SOL", "mainnet", "Base58", 0.70,
         "https://solscan.io/account/{address}"),

        # Polkadot (DOT)
        (r"^1[a-zA-Z0-9]{47}$", "Polkadot", "DOT", "mainnet", "SS58", 0.85,
         "https://polkascan.io/polkadot/account/{address}"),

        # Cosmos (ATOM)
        (r"^cosmos1[a-z0-9]{38}$", "Cosmos", "ATOM", "mainnet", "Bech32", 0.98,
         "https://atomscan.com/accounts/{address}"),

        # Tron (TRX)
        (r"^T[a-zA-Z0-9]{33}$", "Tron", "TRX", "mainnet", "Base58Check", 0.95,
         "https://tronscan.org/#/address/{address}"),

        # Stellar (XLM)
        (r"^G[A-D][A-Z2-7]{54}$", "Stellar", "XLM", "mainnet", "Public Key", 0.98,
         "https://stellar.expert/explorer/public/account/{address}"),

        # Monero (XMR)
        (r"^4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}$", "Monero", "XMR", "mainnet", "Standard", 0.98,
         "https://xmrchain.net/search?value={address}"),
        (r"^8[0-9AB][1-9A-HJ-NP-Za-km-z]{93}$", "Monero", "XMR", "mainnet", "Subaddress", 0.98,
         "https://xmrchain.net/search?value={address}"),

        # Avalanche (AVAX)
        (r"^X-avax[a-z0-9]{39}$", "Avalanche", "AVAX", "X-Chain", "X-Chain", 0.98,
         "https://avascan.info/blockchain/x/address/{address}"),
        (r"^P-avax[a-z0-9]{39}$", "Avalanche", "AVAX", "P-Chain", "P-Chain", 0.98,
         "https://avascan.info/blockchain/p/address/{address}"),
        (r"^C-avax[a-z0-9]{39}$", "Avalanche", "AVAX", "C-Chain", "C-Chain", 0.98,
         "https://avascan.info/blockchain/c/address/{address}"),
        # Note: Avalanche C-Chain also uses 0x addresses (EVM compatible)

        # Binance Smart Chain (uses 0x addresses, EVM compatible)
        # Detected as ETH by default, but can be specified

        # Polygon (uses 0x addresses, EVM compatible)
        # Detected as ETH by default, but can be specified

        # Zcash (ZEC)
        (r"^t1[a-zA-Z0-9]{33}$", "Zcash", "ZEC", "mainnet", "Transparent (t-addr)", 0.95,
         "https://zcashblockexplorer.com/address/{address}"),
        (r"^t3[a-zA-Z0-9]{33}$", "Zcash", "ZEC", "mainnet", "Transparent (t3-addr)", 0.95,
         "https://zcashblockexplorer.com/address/{address}"),
        (r"^zs1[a-z0-9]{76}$", "Zcash", "ZEC", "mainnet", "Shielded (Sapling)", 0.98,
         "https://zcashblockexplorer.com/address/{address}"),

        # Dash (DASH)
        (r"^X[a-km-zA-HJ-NP-Z1-9]{33}$", "Dash", "DASH", "mainnet", "P2PKH", 0.95,
         "https://blockchair.com/dash/address/{address}"),
        (r"^7[a-km-zA-HJ-NP-Z1-9]{33}$", "Dash", "DASH", "mainnet", "P2SH", 0.95,
         "https://blockchair.com/dash/address/{address}"),

        # EOS
        (r"^[a-z1-5.]{1,12}$", "EOS", "EOS", "mainnet", "Account Name", 0.60,
         "https://bloks.io/account/{address}"),

        # NEO
        (r"^A[a-zA-Z0-9]{33}$", "NEO", "NEO", "mainnet", "Address", 0.85,
         "https://neoscan.io/address/{address}"),
        (r"^N[a-zA-Z0-9]{33}$", "NEO", "NEO", "mainnet", "NEO3", 0.90,
         "https://neo3.neotube.io/address/{address}"),

        # NEAR Protocol
        (r"^[a-z0-9_-]{2,64}\.near$", "NEAR Protocol", "NEAR", "mainnet", "Named Account", 0.98,
         "https://explorer.near.org/accounts/{address}"),
        (r"^[a-f0-9]{64}$", "NEAR Protocol", "NEAR", "mainnet", "Implicit Account", 0.50,
         "https://explorer.near.org/accounts/{address}"),

        # Algorand (ALGO)
        (r"^[A-Z2-7]{58}$", "Algorand", "ALGO", "mainnet", "Address", 0.90,
         "https://algoexplorer.io/address/{address}"),

        # Tezos (XTZ)
        (r"^tz[123][a-zA-Z0-9]{33}$", "Tezos", "XTZ", "mainnet", "Address", 0.98,
         "https://tzkt.io/{address}"),
        (r"^KT1[a-zA-Z0-9]{33}$", "Tezos", "XTZ", "mainnet", "Contract", 0.98,
         "https://tzkt.io/{address}"),

        # Hedera (HBAR)
        (r"^0\.0\.[0-9]+$", "Hedera", "HBAR", "mainnet", "Account ID", 0.98,
         "https://hashscan.io/mainnet/account/{address}"),

        # Filecoin (FIL)
        (r"^f[0-3][a-zA-Z0-9]+$", "Filecoin", "FIL", "mainnet", "Address", 0.95,
         "https://filfox.info/en/address/{address}"),

        # Aptos (APT)
        (r"^0x[a-fA-F0-9]{64}$", "Aptos", "APT", "mainnet", "Address", 0.80,
         "https://explorer.aptoslabs.com/account/{address}"),

        # Sui (SUI)
        (r"^0x[a-fA-F0-9]{64}$", "Sui", "SUI", "mainnet", "Address", 0.75,
         "https://suiexplorer.com/address/{address}"),
    ]

    # EVM-compatible chains (all use 0x addresses)
    EVM_CHAINS = {
        "ETH": ("Ethereum", "https://etherscan.io/address/{address}"),
        "BNB": ("BNB Smart Chain", "https://bscscan.com/address/{address}"),
        "MATIC": ("Polygon", "https://polygonscan.com/address/{address}"),
        "AVAX": ("Avalanche C-Chain", "https://snowtrace.io/address/{address}"),
        "FTM": ("Fantom", "https://ftmscan.com/address/{address}"),
        "ARB": ("Arbitrum", "https://arbiscan.io/address/{address}"),
        "OP": ("Optimism", "https://optimistic.etherscan.io/address/{address}"),
        "CELO": ("Celo", "https://celoscan.io/address/{address}"),
        "CRONOS": ("Cronos", "https://cronoscan.com/address/{address}"),
        "GNOSIS": ("Gnosis Chain", "https://gnosisscan.io/address/{address}"),
        "BASE": ("Base", "https://basescan.org/address/{address}"),
    }

    def __init__(self):
        """Initialize the detector with compiled regex patterns."""
        self._compiled_patterns = [
            (re.compile(pattern), coin_name, ticker, network, addr_type, confidence, explorer)
            for pattern, coin_name, ticker, network, addr_type, confidence, explorer in self.PATTERNS
        ]

    def detect(self, address: str) -> CryptoDetectionResult:
        """
        Detect cryptocurrency type from address.

        Args:
            address: The cryptocurrency address to analyze

        Returns:
            CryptoDetectionResult with detection details
        """
        if not address or not isinstance(address, str):
            return CryptoDetectionResult(
                address=address or "",
                detected=False,
            )

        # Clean the address
        address = address.strip()

        # Track best match (highest confidence)
        best_match: Optional[CryptoDetectionResult] = None

        for compiled, coin_name, ticker, network, addr_type, confidence, explorer_template in self._compiled_patterns:
            if compiled.match(address):
                explorer_url = explorer_template.format(address=address) if explorer_template else None

                result = CryptoDetectionResult(
                    address=address,
                    detected=True,
                    coin_name=coin_name,
                    coin_ticker=ticker,
                    network=network,
                    address_type=addr_type,
                    confidence=confidence,
                    explorer_url=explorer_url,
                )

                # Return immediately if high confidence match
                if confidence >= 0.95:
                    return result

                # Keep track of best match
                if best_match is None or confidence > best_match.confidence:
                    best_match = result

        if best_match:
            return best_match

        return CryptoDetectionResult(
            address=address,
            detected=False,
        )

    def detect_evm(self, address: str, chain: str = "ETH") -> CryptoDetectionResult:
        """
        Detect EVM-compatible address with specific chain.

        Args:
            address: The 0x address
            chain: Chain ticker (ETH, BNB, MATIC, etc.)

        Returns:
            CryptoDetectionResult for the specified chain
        """
        if not re.match(r"^0x[a-fA-F0-9]{40}$", address):
            return CryptoDetectionResult(
                address=address,
                detected=False,
            )

        chain = chain.upper()
        if chain in self.EVM_CHAINS:
            coin_name, explorer_template = self.EVM_CHAINS[chain]
            return CryptoDetectionResult(
                address=address,
                detected=True,
                coin_name=coin_name,
                coin_ticker=chain,
                network="mainnet",
                address_type="EVM Address",
                confidence=0.95,
                explorer_url=explorer_template.format(address=address),
            )

        # Default to ETH
        return CryptoDetectionResult(
            address=address,
            detected=True,
            coin_name="Ethereum",
            coin_ticker="ETH",
            network="mainnet",
            address_type="EVM Address",
            confidence=0.85,
            explorer_url=f"https://etherscan.io/address/{address}",
        )

    def detect_all_possible(self, address: str) -> List[CryptoDetectionResult]:
        """
        Get all possible cryptocurrency matches for an address.

        Some addresses (like 0x) could belong to multiple EVM chains.

        Args:
            address: The cryptocurrency address to analyze

        Returns:
            List of all possible CryptoDetectionResult matches
        """
        results = []
        address = address.strip() if address else ""

        for compiled, coin_name, ticker, network, addr_type, confidence, explorer_template in self._compiled_patterns:
            if compiled.match(address):
                explorer_url = explorer_template.format(address=address) if explorer_template else None
                results.append(CryptoDetectionResult(
                    address=address,
                    detected=True,
                    coin_name=coin_name,
                    coin_ticker=ticker,
                    network=network,
                    address_type=addr_type,
                    confidence=confidence,
                    explorer_url=explorer_url,
                ))

        # If it's an EVM address, add all EVM chain possibilities
        if re.match(r"^0x[a-fA-F0-9]{40}$", address):
            for chain, (coin_name, explorer_template) in self.EVM_CHAINS.items():
                if chain != "ETH":  # ETH already in results
                    results.append(CryptoDetectionResult(
                        address=address,
                        detected=True,
                        coin_name=coin_name,
                        coin_ticker=chain,
                        network="mainnet",
                        address_type="EVM Address",
                        confidence=0.80,
                        explorer_url=explorer_template.format(address=address),
                    ))

        # Sort by confidence (highest first)
        results.sort(key=lambda x: x.confidence, reverse=True)

        return results

    def get_supported_cryptocurrencies(self) -> List[dict]:
        """
        Get list of all supported cryptocurrencies.

        Returns:
            List of dicts with coin_name and coin_ticker
        """
        seen = set()
        result = []

        for _, coin_name, ticker, _, _, _, _ in self.PATTERNS:
            if ticker not in seen:
                seen.add(ticker)
                result.append({
                    "coin_name": coin_name,
                    "coin_ticker": ticker,
                })

        # Add EVM chains
        for ticker, (coin_name, _) in self.EVM_CHAINS.items():
            if ticker not in seen:
                seen.add(ticker)
                result.append({
                    "coin_name": coin_name,
                    "coin_ticker": ticker,
                })

        return sorted(result, key=lambda x: x["coin_name"])


# Singleton instance for convenience
_detector = CryptoAddressDetector()


def detect_crypto_address(address: str) -> CryptoDetectionResult:
    """
    Convenience function to detect cryptocurrency type from address.

    Args:
        address: The cryptocurrency address to analyze

    Returns:
        CryptoDetectionResult with detection details
    """
    return _detector.detect(address)


def detect_all_crypto_addresses(address: str) -> List[CryptoDetectionResult]:
    """
    Get all possible cryptocurrency matches for an address.

    Args:
        address: The cryptocurrency address to analyze

    Returns:
        List of all possible CryptoDetectionResult matches
    """
    return _detector.detect_all_possible(address)
