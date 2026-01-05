"""
Cryptocurrency Address Detection Utility

Automatically detects cryptocurrency type from wallet address format.
Supports 20+ major cryptocurrencies with comprehensive pattern matching.
Includes checksum validation for Bitcoin, Ethereum, Litecoin, and other major chains.
"""

import re
import hashlib
from dataclasses import dataclass
from typing import Optional, List, Tuple

# Try to import base58 for Base58Check validation
try:
    import base58
    HAS_BASE58 = True
except ImportError:
    HAS_BASE58 = False


# =============================================================================
# Checksum Validators
# =============================================================================


class ChecksumValidator:
    """Base class for cryptocurrency address checksum validators."""

    @staticmethod
    def validate(address: str) -> Optional[bool]:
        """
        Validate the checksum of an address.

        Returns:
            True if checksum is valid
            False if checksum is invalid
            None if checksum cannot be validated (unsupported format)
        """
        raise NotImplementedError


class Base58CheckValidator(ChecksumValidator):
    """
    Validates Base58Check encoded addresses (Bitcoin, Litecoin, Dogecoin, etc.)

    Base58Check encoding includes a 4-byte checksum at the end which is the
    first 4 bytes of SHA256(SHA256(version + payload)).
    """

    @staticmethod
    def validate(address: str) -> Optional[bool]:
        """Validate a Base58Check encoded address."""
        if not HAS_BASE58:
            return None  # Cannot validate without base58 library

        try:
            # Decode the Base58 address
            decoded = base58.b58decode(address)

            # Must have at least 5 bytes (1 version + checksum)
            if len(decoded) < 5:
                return False

            # Split into payload (version + data) and checksum
            payload = decoded[:-4]
            checksum = decoded[-4:]

            # Calculate expected checksum: first 4 bytes of double SHA256
            hash1 = hashlib.sha256(payload).digest()
            hash2 = hashlib.sha256(hash1).digest()
            expected_checksum = hash2[:4]

            return checksum == expected_checksum

        except Exception:
            return False


class Bech32Validator(ChecksumValidator):
    """
    Validates Bech32 and Bech32m encoded addresses (Bitcoin SegWit, Litecoin).

    Implements BIP-173 (Bech32) and BIP-350 (Bech32m) checksum validation.
    """

    # Bech32 character set
    CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

    # Generator polynomial for Bech32
    BECH32_CONST = 1
    BECH32M_CONST = 0x2bc830a3

    @classmethod
    def _polymod(cls, values: List[int]) -> int:
        """Internal function that computes the Bech32 checksum."""
        generator = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
        chk = 1
        for value in values:
            top = chk >> 25
            chk = (chk & 0x1ffffff) << 5 ^ value
            for i in range(5):
                chk ^= generator[i] if ((top >> i) & 1) else 0
        return chk

    @classmethod
    def _hrp_expand(cls, hrp: str) -> List[int]:
        """Expand the HRP into values for checksum computation."""
        return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

    @classmethod
    def _verify_checksum(cls, hrp: str, data: List[int]) -> Optional[str]:
        """Verify checksum and return encoding type (bech32 or bech32m)."""
        const = cls._polymod(cls._hrp_expand(hrp) + data)
        if const == cls.BECH32_CONST:
            return "bech32"
        if const == cls.BECH32M_CONST:
            return "bech32m"
        return None

    @classmethod
    def validate(cls, address: str) -> Optional[bool]:
        """Validate a Bech32 or Bech32m encoded address."""
        address = address.lower()

        # Find the separator (last '1' in the address)
        pos = address.rfind('1')
        if pos < 1 or pos + 7 > len(address):
            return False

        # Check that data part uses only valid characters
        data_part = address[pos + 1:]
        if not all(c in cls.CHARSET for c in data_part):
            return False

        # Extract HRP and convert data part to integers
        hrp = address[:pos]
        data = [cls.CHARSET.find(c) for c in data_part]

        # Verify checksum
        encoding = cls._verify_checksum(hrp, data)
        return encoding is not None


class EIP55Validator(ChecksumValidator):
    """
    Validates Ethereum EIP-55 mixed-case checksum addresses.

    EIP-55 uses the Keccak-256 hash of the lowercase address to determine
    which characters should be uppercase.
    """

    @staticmethod
    def _keccak256(data: bytes) -> bytes:
        """
        Compute Keccak-256 hash.

        Note: Python's sha3_256 is SHA3-256 (FIPS 202), NOT Keccak-256.
        For EIP-55 we need the original Keccak-256 (pre-standardization).
        """
        # Try pycryptodome first (correct Keccak-256)
        try:
            from Crypto.Hash import keccak
            k = keccak.new(digest_bits=256)
            k.update(data)
            return k.digest()
        except ImportError:
            pass

        # Try pysha3 (pip install pysha3)
        try:
            import sha3
            k = sha3.keccak_256()
            k.update(data)
            return k.digest()
        except ImportError:
            pass

        # Try eth_hash with pycryptodome backend
        try:
            from eth_hash.auto import keccak
            return keccak.new(data).digest()
        except ImportError:
            pass

        # Fallback: cannot validate (do NOT use hashlib.sha3_256 - it's different!)
        return b""

    @classmethod
    def validate(cls, address: str) -> Optional[bool]:
        """
        Validate an Ethereum address using EIP-55 checksum.

        Note: All-lowercase and all-uppercase addresses are considered valid
        (they bypass checksum validation per EIP-55 spec).
        """
        if not address.startswith("0x"):
            return False

        addr_body = address[2:]

        # All lowercase or all uppercase bypasses checksum
        if addr_body.islower() or addr_body.isupper():
            return True

        # Mixed case - need to validate checksum
        addr_lower = addr_body.lower()
        hash_bytes = cls._keccak256(addr_lower.encode('ascii'))

        if not hash_bytes:
            return None  # Cannot validate without Keccak

        hash_hex = hash_bytes.hex()

        # Check each character
        for i, char in enumerate(addr_lower):
            if char in '0123456789':
                continue
            # For a-f characters, check if hash nibble >= 8 means uppercase
            hash_nibble = int(hash_hex[i], 16)
            expected_upper = hash_nibble >= 8
            actual_upper = addr_body[i].isupper()
            if expected_upper != actual_upper:
                return False

        return True


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
    # Checksum validation fields
    checksum_valid: Optional[bool] = None  # True/False/None (cannot validate)
    checksum_type: Optional[str] = None  # "Base58Check", "Bech32", "EIP55", etc.

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
            "checksum_valid": self.checksum_valid,
            "checksum_type": self.checksum_type,
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

    # Mapping of address types to their checksum validators
    CHECKSUM_VALIDATORS = {
        # Bitcoin Base58Check addresses
        "P2PKH (Legacy)": ("Base58Check", Base58CheckValidator),
        "P2SH (SegWit Compatible)": ("Base58Check", Base58CheckValidator),
        # Bitcoin Bech32/Bech32m addresses
        "Bech32 (Native SegWit)": ("Bech32", Bech32Validator),
        "Bech32m (Taproot)": ("Bech32m", Bech32Validator),
        # Ethereum EIP-55
        "EVM Address": ("EIP-55", EIP55Validator),
        # Litecoin
        "P2PKH": ("Base58Check", Base58CheckValidator),  # Litecoin legacy
        "P2SH": ("Base58Check", Base58CheckValidator),  # Litecoin P2SH
        "P2SH (SegWit)": ("Base58Check", Base58CheckValidator),
        # Dogecoin
        # "P2PKH": already mapped above
        # Tron
        "Base58Check": ("Base58Check", Base58CheckValidator),
        # Ripple
        "Classic": ("Base58Check", Base58CheckValidator),
        # Zcash transparent
        "Transparent (t-addr)": ("Base58Check", Base58CheckValidator),
        "Transparent (t3-addr)": ("Base58Check", Base58CheckValidator),
        # Dash
        # "P2PKH": already mapped above
        # NEO
        "Address": ("Base58Check", Base58CheckValidator),
        "NEO3": ("Base58Check", Base58CheckValidator),
    }

    def __init__(self):
        """Initialize the detector with compiled regex patterns."""
        self._compiled_patterns = [
            (re.compile(pattern), coin_name, ticker, network, addr_type, confidence, explorer)
            for pattern, coin_name, ticker, network, addr_type, confidence, explorer in self.PATTERNS
        ]

    def _validate_checksum(self, address: str, address_type: str) -> Tuple[Optional[bool], Optional[str]]:
        """
        Validate checksum for an address based on its type.

        Returns:
            Tuple of (checksum_valid, checksum_type)
        """
        if address_type in self.CHECKSUM_VALIDATORS:
            checksum_type, validator_class = self.CHECKSUM_VALIDATORS[address_type]
            checksum_valid = validator_class.validate(address)
            return checksum_valid, checksum_type
        return None, None

    def detect(self, address: str, validate_checksum: bool = True) -> CryptoDetectionResult:
        """
        Detect cryptocurrency type from address.

        Args:
            address: The cryptocurrency address to analyze
            validate_checksum: Whether to perform checksum validation (default True)

        Returns:
            CryptoDetectionResult with detection details including checksum validation
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

                # Validate checksum if requested
                checksum_valid = None
                checksum_type = None
                if validate_checksum:
                    checksum_valid, checksum_type = self._validate_checksum(address, addr_type)
                    # Boost confidence if checksum is valid, reduce if invalid
                    if checksum_valid is True:
                        confidence = min(0.99, confidence + 0.03)
                    elif checksum_valid is False:
                        confidence = max(0.1, confidence - 0.3)

                result = CryptoDetectionResult(
                    address=address,
                    detected=True,
                    coin_name=coin_name,
                    coin_ticker=ticker,
                    network=network,
                    address_type=addr_type,
                    confidence=confidence,
                    explorer_url=explorer_url,
                    checksum_valid=checksum_valid,
                    checksum_type=checksum_type,
                )

                # Return immediately if high confidence match with valid checksum
                if confidence >= 0.95 and checksum_valid is not False:
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

    def detect_evm(self, address: str, chain: str = "ETH", validate_checksum: bool = True) -> CryptoDetectionResult:
        """
        Detect EVM-compatible address with specific chain.

        Args:
            address: The 0x address
            chain: Chain ticker (ETH, BNB, MATIC, etc.)
            validate_checksum: Whether to perform EIP-55 checksum validation

        Returns:
            CryptoDetectionResult for the specified chain
        """
        if not re.match(r"^0x[a-fA-F0-9]{40}$", address):
            return CryptoDetectionResult(
                address=address,
                detected=False,
            )

        # Validate EIP-55 checksum if requested
        checksum_valid = None
        checksum_type = None
        confidence_adjustment = 0.0
        if validate_checksum:
            checksum_valid = EIP55Validator.validate(address)
            checksum_type = "EIP-55"
            if checksum_valid is True:
                confidence_adjustment = 0.03
            elif checksum_valid is False:
                confidence_adjustment = -0.3

        chain = chain.upper()
        if chain in self.EVM_CHAINS:
            coin_name, explorer_template = self.EVM_CHAINS[chain]
            confidence = min(0.99, max(0.1, 0.95 + confidence_adjustment))
            return CryptoDetectionResult(
                address=address,
                detected=True,
                coin_name=coin_name,
                coin_ticker=chain,
                network="mainnet",
                address_type="EVM Address",
                confidence=confidence,
                explorer_url=explorer_template.format(address=address),
                checksum_valid=checksum_valid,
                checksum_type=checksum_type,
            )

        # Default to ETH
        confidence = min(0.99, max(0.1, 0.85 + confidence_adjustment))
        return CryptoDetectionResult(
            address=address,
            detected=True,
            coin_name="Ethereum",
            coin_ticker="ETH",
            network="mainnet",
            address_type="EVM Address",
            confidence=confidence,
            explorer_url=f"https://etherscan.io/address/{address}",
            checksum_valid=checksum_valid,
            checksum_type=checksum_type,
        )

    def detect_all_possible(self, address: str, validate_checksum: bool = True) -> List[CryptoDetectionResult]:
        """
        Get all possible cryptocurrency matches for an address.

        Some addresses (like 0x) could belong to multiple EVM chains.

        Args:
            address: The cryptocurrency address to analyze
            validate_checksum: Whether to perform checksum validation

        Returns:
            List of all possible CryptoDetectionResult matches
        """
        results = []
        address = address.strip() if address else ""

        for compiled, coin_name, ticker, network, addr_type, confidence, explorer_template in self._compiled_patterns:
            if compiled.match(address):
                explorer_url = explorer_template.format(address=address) if explorer_template else None

                # Validate checksum if requested
                checksum_valid = None
                checksum_type = None
                if validate_checksum:
                    checksum_valid, checksum_type = self._validate_checksum(address, addr_type)
                    # Adjust confidence based on checksum
                    if checksum_valid is True:
                        confidence = min(0.99, confidence + 0.03)
                    elif checksum_valid is False:
                        confidence = max(0.1, confidence - 0.3)

                results.append(CryptoDetectionResult(
                    address=address,
                    detected=True,
                    coin_name=coin_name,
                    coin_ticker=ticker,
                    network=network,
                    address_type=addr_type,
                    confidence=confidence,
                    explorer_url=explorer_url,
                    checksum_valid=checksum_valid,
                    checksum_type=checksum_type,
                ))

        # If it's an EVM address, add all EVM chain possibilities
        if re.match(r"^0x[a-fA-F0-9]{40}$", address):
            # Get EIP-55 checksum validation once for all EVM chains
            evm_checksum_valid = None
            if validate_checksum:
                evm_checksum_valid = EIP55Validator.validate(address)

            for chain, (coin_name, explorer_template) in self.EVM_CHAINS.items():
                if chain != "ETH":  # ETH already in results
                    base_confidence = 0.80
                    if validate_checksum and evm_checksum_valid is True:
                        base_confidence = min(0.99, base_confidence + 0.03)
                    elif validate_checksum and evm_checksum_valid is False:
                        base_confidence = max(0.1, base_confidence - 0.3)

                    results.append(CryptoDetectionResult(
                        address=address,
                        detected=True,
                        coin_name=coin_name,
                        coin_ticker=chain,
                        network="mainnet",
                        address_type="EVM Address",
                        confidence=base_confidence,
                        explorer_url=explorer_template.format(address=address),
                        checksum_valid=evm_checksum_valid if validate_checksum else None,
                        checksum_type="EIP-55" if validate_checksum else None,
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
