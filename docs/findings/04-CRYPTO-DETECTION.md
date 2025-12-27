# Cryptocurrency Address Detection Feature

## Overview

Implemented automatic cryptocurrency address detection that identifies the coin type from the address format alone. This allows users to paste any crypto address and have Basset Hound automatically detect the associated cryptocurrency.

## Implementation Date

2025-12-27

## Problem Statement

Previously, users had to manually specify which cryptocurrency an address belonged to. This was error-prone and tedious, especially when dealing with multiple addresses across different cryptocurrencies. The goal was to create a unified "crypto address" field that automatically detects the coin type.

## Solution

Created a comprehensive cryptocurrency address detection utility (`api/utils/crypto_detector.py`) that uses regex patterns to identify 20+ cryptocurrencies based on their unique address formats.

## Supported Cryptocurrencies

| Cryptocurrency | Ticker | Address Patterns |
|---------------|--------|------------------|
| Bitcoin | BTC | P2PKH (1...), P2SH (3...), Bech32 (bc1q...), Taproot (bc1p...) |
| Ethereum | ETH | 0x + 40 hex chars |
| Litecoin | LTC | L..., M..., ltc1... |
| Dogecoin | DOGE | D..., A... |
| Ripple | XRP | r..., X... (X-Address) |
| Cardano | ADA | addr1..., Ae2..., DdzFF... |
| Solana | SOL | Base58 32-44 chars |
| Polkadot | DOT | 1... (47+ chars) |
| Monero | XMR | 4... or 8... (95 chars) |
| Tron | TRX | T... (34 chars) |
| Stellar | XLM | G... (56 chars) |
| Cosmos | ATOM | cosmos1... |
| Avalanche | AVAX | avax1... or 0x... |
| Zcash | ZEC | t1..., t3..., zs1..., zc... |
| Dash | DASH | X... (34 chars) |
| Tezos | XTZ | tz1..., tz2..., tz3..., KT1... |
| Hedera | HBAR | 0.0.NNNNNN |
| NEAR Protocol | NEAR | *.near |
| Filecoin | FIL | f0..., f1..., f2..., f3... |

### EVM-Compatible Chains

All share the same 0x address format but can be distinguished with chain hints:
- Ethereum (ETH)
- BNB Smart Chain (BNB)
- Polygon (MATIC)
- Arbitrum (ARB)
- Optimism (OP)
- Avalanche C-Chain (AVAX)
- Fantom (FTM)
- Cronos (CRO)
- Base (BASE)

## API Endpoints

### POST /utils/detect-crypto
Detect cryptocurrency from a single address.

```json
Request:
{
  "address": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
}

Response:
{
  "address": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
  "detected": true,
  "coin_name": "Bitcoin",
  "coin_ticker": "BTC",
  "network": "mainnet",
  "address_type": "Bech32 (Native SegWit)",
  "confidence": 0.98,
  "explorer_url": "https://www.blockchain.com/btc/address/bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
}
```

### GET /utils/detect-crypto/{address}
Same as POST but via GET request for simple testing.

### POST /utils/detect-crypto/all
Get all possible matches for an address (useful for ambiguous formats like 0x).

### POST /utils/detect-crypto/batch
Batch detection for multiple addresses (max 100).

### GET /utils/crypto/supported
List all supported cryptocurrencies.

### GET /utils/crypto/validate/{address}
Simple validation (true/false) for any crypto address.

## Data Config Integration

Added `crypto_address` field type to `data_config.yaml`:

```yaml
field_types:
  crypto_address:
    html_input: text
    auto_detect: true
    detection_endpoint: /utils/detect-crypto
```

The `auto_detect: true` flag tells the frontend to call the detection endpoint when a value is entered, displaying the detected coin ticker next to the input.

## Detection Algorithm

1. **Normalization**: Strip whitespace, convert to appropriate case
2. **Pattern Matching**: Test against cryptocurrency-specific regex patterns
3. **Confidence Scoring**: Assign confidence based on pattern specificity
   - 0.98+: Unique patterns (Bech32, XMR, XLM)
   - 0.95: Distinctive patterns (XRP, ADA, TRX)
   - 0.85: Shared patterns (0x addresses default to ETH)
   - 0.70-0.80: Ambiguous patterns (Base58 without prefix)
4. **Explorer URL Generation**: Construct block explorer URL for verification

## Test Coverage

Created comprehensive pytest test suite with 85 tests covering:

- All major cryptocurrency address types
- Multiple address formats per coin (Legacy, SegWit, Bech32, Taproot for BTC)
- Invalid/malformed addresses
- Edge cases (empty strings, None, special characters)
- Whitespace handling
- Confidence level verification
- Explorer URL generation
- Batch detection
- EVM chain hints

## Files Created

| File | Description |
|------|-------------|
| `api/utils/__init__.py` | Utils module exports |
| `api/utils/crypto_detector.py` | Core detection logic (~400 lines) |
| `api/routers/utils.py` | API endpoints (~180 lines) |
| `tests/test_crypto_detector.py` | 85 comprehensive tests (~1200 lines) |

## Performance Considerations

- Detection is O(n) where n is the number of crypto patterns (~25)
- Each detection takes <1ms on average
- Batch processing is efficient with early-exit on first match
- Singleton pattern for detector instance reuse

## Future Enhancements

1. **Frontend Integration**: Display detected ticker next to crypto input fields
2. **Checksum Validation**: Verify address checksums for Bitcoin, Ethereum
3. **Address Balance Lookup**: Optional integration with blockchain APIs
4. **Historical Address Detection**: Detect deprecated address formats
5. **Custom Coin Support**: Allow users to add custom coin patterns

## Security Notes

- No external API calls during detection (all regex-based)
- Address format validation only, not ownership verification
- Explorer URLs are constructed, not validated against actual blockchain data
