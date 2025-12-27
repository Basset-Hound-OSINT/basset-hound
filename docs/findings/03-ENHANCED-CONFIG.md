# Enhanced Data Configuration

## Overview

Created a comprehensive `data_config_enhanced.yaml` that supports 50+ social networks and identifier types, making Basset Hound suitable for extensive OSINT investigations.

## Configuration Structure

### Sections Added

1. **Profile Picture Section** - Primary identification image
2. **Personal Information** - Core identity data
3. **Social Media - Major Platforms** - Facebook, Instagram, Twitter, etc.
4. **Social Media - Professional** - LinkedIn, GitHub, Stack Overflow
5. **Social Media - Federated/Decentralized** - Mastodon, Bluesky, Nostr
6. **Forums and Communities** - Reddit, Hacker News, Discord
7. **Gaming Platforms** - Steam, Xbox, PlayStation
8. **Financial/Crypto** - PayPal, Venmo, crypto addresses
9. **Technical Identifiers** - IP, MAC, domains
10. **Devices** - Physical device tracking
11. **Tagged People** - Relationship management

### Social Networks Supported

#### Major Platforms
- Facebook, Instagram, Twitter/X, TikTok, YouTube
- Snapchat, Pinterest, LinkedIn, WhatsApp

#### Professional Networks
- LinkedIn, GitHub, GitLab, Bitbucket
- Stack Overflow, Medium, Dev.to
- Dribbble, Behance

#### Federated/Decentralized
- Mastodon, Bluesky, Threads
- Nostr, Lemmy, Pixelfed, PeerTube
- Matrix, XMPP/Jabber

#### Forums & Communities
- Reddit, Hacker News
- Discord, Slack, Telegram
- Signal, WhatsApp, WeChat, Line, KakaoTalk

#### Gaming
- Steam, Xbox, PlayStation, Nintendo
- Epic Games, Twitch, Spotify

#### Financial/Crypto
- PayPal, Venmo, Cash App, Zelle
- Coinbase, Binance
- Ethereum address, Bitcoin address

### Field Types

Each field includes:
- **id**: Unique identifier
- **label**: Display name
- **type**: Data type (string, url, email, component, file)
- **placeholder**: Input hint
- **multiple**: Whether multiple values allowed
- **components**: Sub-fields for complex data
- **url_pattern**: Link template for identifiers

### Example Field Definition

```yaml
- id: mastodon
  label: Mastodon
  type: component
  multiple: true
  components:
    - id: username
      type: string
      label: Username
    - id: instance
      type: string
      label: Instance
      placeholder: mastodon.social
    - id: url
      type: url
      label: Profile URL
    - id: email
      type: email
      label: Associated Email
      multiple: true
    - id: comment
      type: comment
      label: Notes
```

## Technical Identifier Types

### Network Identifiers
- IP Address (v4/v6)
- MAC Address
- Domain Names
- Email Addresses

### Security Identifiers
- PGP Key ID
- SSH Key Fingerprint
- Crypto Wallet Addresses

## Usage

### API Endpoints

```bash
# Get enhanced configuration
GET /api/v1/config/enhanced

# List all available identifier types
GET /api/v1/config/identifiers

# Validate a configuration
POST /api/v1/config/validate
```

### Dynamic Schema

The configuration drives:
1. Profile editor UI generation
2. Neo4j schema creation
3. Search field indexing
4. Data validation rules

## Integration with MCP

The enhanced configuration enables MCP tools to:
- Query available identifier types
- Validate input data
- Generate proper storage paths
- Create URL patterns for external lookups

## Adding New Identifier Types

To add a new social network or identifier:

```yaml
sections:
  - id: social_new_platform
    label: New Platform
    fields:
      - id: platform_username
        label: Username
        type: string
        url_pattern: https://newplatform.com/user/{value}
        multiple: true
```

## Migration from Basic Config

1. Backup existing `data_config.yaml`
2. Copy `data_config_enhanced.yaml` to `data_config.yaml`
3. Run schema update: `neo4j_handler.setup_schema_from_config(config)`
4. Existing data will be preserved

## Future Enhancements

1. **Custom Field Types**: User-defined field types
2. **Validation Rules**: Regex patterns, required combinations
3. **Field Dependencies**: Conditional field display
4. **Import/Export**: Configuration sharing
