# Basset Hound Mobile App: Master Plan & Scope
**Date**: 2026-05-07  
**Status**: SCOPE & ARCHITECTURE PLANNING  
**Objective**: Define mobile companion application for field data collection and sensor integration

---

## Project Vision

**Basset Hound Mobile** is a companion mobile application (iOS/Android) for law enforcement, private investigators, and OSINT researchers to collect, capture, and upload investigative data directly from mobile devices to the cloud-based Basset Hound platform.

### Use Cases
1. **Field Evidence Collection**: Capture photos, video, audio at investigation scenes
2. **Sensor Data Capture**: Access device sensors (GPS, accelerometer, magnetometer, camera, microphone)
3. **Mobile Data Mining**: Extract and upload contacts, messages, call logs, media
4. **Real-Time Sync**: Upload to central Basset Hound instance immediately or queue for later
5. **Investigation Tracking**: Tag, organize, and link mobile data to existing investigations
6. **Officer Coordination**: Multiple officers can contribute data to same investigation
7. **Secure Chain of Custody**: Metadata, timestamps, officer attribution, encryption

### Inspiration
- **PhyPhox**: Physics experiment app for sensor data - but for investigations
- **Law Enforcement Mobile Tools**: Field data capture systems (existing NSA/CIA tools)
- **IoT Data Aggregation**: Phones as "sensor boxes"

---

## Scope Definition

### IN SCOPE
1. **Data Collection**
   - Camera (photo + video)
   - Audio recording (voice notes)
   - Phone sensors: GPS, accelerometer, magnetometer, gyroscope, light sensor
   - Device storage access: contacts, messages, call logs, photos/videos, documents
   - Network info, connected devices, Bluetooth devices

2. **Basset Hound Integration**
   - REST API client for Basset Hound cloud instance
   - OAuth2 authentication to cloud
   - Automatic/manual sync to investigations
   - Real-time upload or queue for offline capability

3. **Investigation Management**
   - Create new investigations
   - Join existing investigations
   - Organize collected data by category
   - Tag and annotate media
   - Link to existing entities (persons, locations, organizations)

4. **Security & Privacy**
   - End-to-end encryption for sensitive data
   - Role-based access control (officer permissions)
   - Chain of custody logging (who collected what, when)
   - Secure credential storage
   - Data deletion policies

5. **Platforms**
   - **Phase 1**: Android (primary, largest LE market)
   - **Phase 2**: iOS (secondary)
   - **Future**: Windows Mobile, other platforms

### OUT OF SCOPE
1. **Kubernetes/Infrastructure**: Not mobile-related
2. **Multi-region HA**: Cloud responsibility, not app
3. **Advanced ML in App**: Keep app lightweight, ML runs on server
4. **Complex UI**: Simple, field-friendly interface
5. **Offline-first Database**: Server-side database responsibility
6. **Payment Systems**: Free/enterprise licensing handled elsewhere
7. **Social Networking**: Not collaboration tool

### EXPLICITLY EXCLUDED (Per User)
- Kubernetes deployment
- Multi-region HA/failover setup
- Advanced ML model training in app
- Mobile app UIs for other projects (basset-verify, browser, etc.)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│           Basset Hound Mobile App (iOS/Android)             │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Camera     │  │   Sensors    │  │   Storage    │    │
│  │   & Audio    │  │   (GPS,      │  │   (Contacts, │    │
│  │              │  │   Accel,     │  │    Messages, │    │
│  │              │  │   Mag)       │  │    Docs)     │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │              │
│         └─────────────────┼─────────────────┘              │
│                           │                                │
│                 ┌─────────▼────────┐                       │
│                 │   Data Manager   │                       │
│                 │   & Encryption   │                       │
│                 └─────────┬────────┘                       │
│                           │                                │
│                 ┌─────────▼──────────┐                     │
│                 │  Basset Hound API  │                     │
│                 │  Client (REST/SSL) │                     │
│                 └─────────┬──────────┘                     │
│                           │                                │
└───────────────────────────┼────────────────────────────────┘
                            │
                ┌───────────▼──────────┐
                │  Cloud Basset Hound  │
                │  ├─ REST API         │
                │  ├─ Neo4j Graph DB   │
                │  ├─ Redis Cache      │
                │  ├─ File Storage     │
                │  └─ Analytics        │
                └──────────────────────┘
```

---

## Technical Stack

### Mobile (Frontend)
- **Android**: Kotlin + Jetpack Compose (modern, type-safe)
- **iOS**: Swift + SwiftUI (native performance)
- **Shared Logic**: Kotlin Multiplatform (KMP) or similar for code reuse
- **Storage**: SQLite (local queue), Encrypted SharedPreferences
- **Networking**: Retrofit + OkHttp (Android), URLSession (iOS)
- **Permissions**: Modern permission model per platform

### Communication
- **Protocol**: REST API (HTTPS/TLS 1.3)
- **Authentication**: OAuth2 + JWT tokens
- **Encryption**: AES-256 for sensitive data at rest, TLS for transit
- **Sync**: Queue-based with exponential backoff

### Cloud Integration
- **Base URL**: Configurable Basset Hound instance (self-hosted or cloud)
- **API Client**: Same REST API as web dashboard
- **Authentication**: OAuth2 flow (officer sign-in)
- **Data Format**: JSON with metadata (officer, timestamp, source device)

---

## Data Model

### Investigation Schema
```
Investigation {
  id: UUID
  title: string
  description: string
  officers: [Officer]
  status: "active" | "closed" | "archived"
  entities: [Entity]  # Persons, locations, organizations
  created_at: timestamp
  created_by: Officer
}

CollectedData {
  id: UUID
  investigation_id: UUID
  type: "photo" | "video" | "audio" | "contact" | "message" | "sensor" | "document"
  source: "camera" | "audio" | "gps" | "device_storage" | "sensor"
  data: binary | json
  metadata: {
    timestamp: timestamp
    location: {lat, lon, accuracy}
    officer: Officer
    device_info: {model, os, version}
    sensor_type: string  # for sensor data
    encryption: "AES-256"
  }
  linked_entities: [Entity]
  tags: [string]
  notes: string
  synced: boolean
  sync_timestamp: timestamp
}

Officer {
  id: UUID
  name: string
  email: string
  badge_id: string
  organization: string
  role: "investigator" | "supervisor" | "admin"
  permissions: [string]
}
```

---

## Feature Set (Phased)

### Phase 1: MVP (Android)
**Duration**: 3-4 months | **Team**: 2-3 developers

**Core Features**:
- ✅ User authentication (OAuth2 to cloud)
- ✅ Investigation management (create, join, list)
- ✅ Photo capture and upload
- ✅ Audio recording and upload
- ✅ GPS location tracking
- ✅ Basic tags and notes
- ✅ Offline queue (sync when online)
- ✅ Encryption at rest + TLS transit
- ✅ Chain of custody logging
- ✅ Integration with Basset Hound REST API

**UI Screens**:
- Login/authentication
- Investigation list
- Investigation detail
- New data capture (tabs: photo, audio, location, notes)
- Data queue (pending uploads)
- Settings (account, encryption, sync)

### Phase 2: Enhancement (Android + iOS)
**Duration**: 2-3 months | **Team**: 2-3 developers

**Additional Features**:
- ✅ iOS port (Swift + SwiftUI)
- ✅ Device storage access (contacts, messages, documents)
- ✅ Advanced sensors (accelerometer, magnetometer, light)
- ✅ Video recording
- ✅ Bluetooth device discovery
- ✅ Network information capture
- ✅ Advanced filtering/search of collected data
- ✅ Collaboration features (see other officers' contributions)
- ✅ Role-based permissions

**UI Enhancements**:
- Media gallery view
- Advanced filtering/search
- Collaboration panel
- Sensor data visualization
- Device info capture UI

### Phase 3: Advanced Features
**Duration**: 2-3 months | **Team**: 2-3 developers

**Advanced Features**:
- ✅ Face recognition integration (detect faces in photos)
- ✅ OCR for document scanning
- ✅ Sensor data analytics (motion patterns, etc.)
- ✅ Offline-first mode (full app functionality without internet)
- ✅ Advanced encryption (biometric unlock)
- ✅ Report generation from collected data
- ✅ API for third-party integrations
- ✅ Backup/restore functionality

### Future Phases
- Windows Mobile port
- Wearable device support (smartwatch sensors)
- AR visualization for location-based data
- ML-powered automatic tagging
- Advanced timeline visualization

---

## Permissions Required

### Android
```
CAMERA
RECORD_AUDIO
ACCESS_FINE_LOCATION
ACCESS_COARSE_LOCATION
READ_CONTACTS
READ_CALL_LOG
READ_SMS
READ_EXTERNAL_STORAGE
WRITE_EXTERNAL_STORAGE
INTERNET
ACCESS_NETWORK_STATE
BLUETOOTH
BLUETOOTH_ADMIN
ACCELEROMETER
MAGNETOMETER
GYROSCOPE
LIGHT_SENSOR
```

### iOS
```
NSCameraUsageDescription
NSMicrophoneUsageDescription
NSLocationWhenInUseUsageDescription
NSContactsUsageDescription
NSPhotoLibraryUsageDescription
NSMotionUsageDescription
```

---

## Security & Compliance

### Encryption
- **At Rest**: AES-256 using SQLite encryption (SQLCipher)
- **In Transit**: TLS 1.3 minimum
- **Sensitive Data**: PII encrypted with app-specific key
- **Key Storage**: Secure enclave (iOS) / Keystore (Android)

### Authentication
- OAuth2 with PKCE (Proof Key for Code Exchange)
- JWT token storage in secure storage
- Token refresh with auto-renewal
- Biometric unlock support

### Audit Trail
- Every action logged with officer ID, timestamp, action type
- Immutable audit log (cannot be edited after creation)
- Sync audit trail to cloud
- Exportable audit reports

### Compliance
- GDPR: Right to be forgotten (soft delete)
- CCPA: Data minimization, user control
- Law Enforcement: Chain of custody preservation
- HIPAA: If handling medical data (optional encryption)

---

## API Endpoints Required

The app will use existing Basset Hound REST API endpoints plus new ones:

### Existing Endpoints Used
- `POST /api/v1/auth/login` - OAuth2 flow
- `POST /api/v1/projects` - Create investigation
- `GET /api/v1/projects` - List investigations
- `POST /api/v1/projects/{id}/entities` - Create entity (person, location, etc.)
- `POST /api/v1/projects/{id}/media` - Upload media files

### New Endpoints (To Implement in Basset Hound)
- `POST /api/v1/mobile/auth/token-refresh` - Refresh JWT
- `POST /api/v1/mobile/data/upload` - Batch upload collected data
- `GET /api/v1/mobile/data/{investigation_id}` - Sync queued data status
- `POST /api/v1/mobile/audit-log` - Log officer actions
- `GET /api/v1/mobile/permissions` - Get officer permissions

---

## Development Roadmap

```
Timeline: 9-10 months total

Q3 2026:
  - Plan & design (1 month) - COMPLETE
  - MVP Android (3 months)
    - Authentication
    - Core data capture
    - Basic sync
  
Q4 2026:
  - iOS port (2 months)
  - Phase 2 features (1 month)
    - Storage access
    - Advanced sensors
    - Collaboration
  
Q1 2027:
  - Phase 3 features (3 months)
    - Face detection
    - OCR
    - Advanced analytics
    - Offline-first
  
Q2+ 2027:
  - Additional platforms
  - Advanced features
  - Maintenance & support
```

---

## Team Structure

**Phase 1 (MVP)**: 2-3 developers
- Lead: Android developer (Kotlin + Jetpack)
- Backend liaison: API client + integration
- QA: Testing on real devices

**Phase 2 (iOS)**: +1 iOS developer
- iOS lead: Swift + SwiftUI
- Keep Android devs for continued enhancement
- Shared architecture/API work

**Phase 3+**: +1 ML/data scientist (optional)
- Advanced analytics
- Face recognition integration
- ML-based auto-tagging

---

## Success Metrics

### Technical
- ✅ <100MB app size (Android)
- ✅ <150MB app size (iOS)
- ✅ <5% battery drain during 8h investigation
- ✅ Offline queue handles 1000+ items
- ✅ Sync <10 minutes for 100MB of data
- ✅ Encryption/decryption <100ms
- ✅ 99.9% uptime (depends on cloud backend)

### Business
- ✅ 1,000+ installs in first year
- ✅ <2 star app rating (law enforcement expects stability, not features)
- ✅ 50+ active investigations per month
- ✅ 100,000+ data items collected per month
- ✅ <1% data loss rate
- ✅ <30 second average upload time

### Operational
- ✅ Officer onboarding <5 minutes
- ✅ Field deployment <2 hours
- ✅ Data recovery time <1 hour
- ✅ Support response <4 hours

---

## Known Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Device OS updates break app | High | Continuous CI/CD testing, fast update cycle |
| Encryption key loss | Critical | Backup to cloud, officer recovery flow |
| Network unavailability | High | Offline queue with 30-day retention |
| Data privacy/leaks | Critical | End-to-end encryption, audit logging |
| Officer mistakes (wrong investigation) | Medium | Confirmation dialogs, undo functionality |
| Device theft | High | Remote wipe capability, pin protection |
| Sync conflicts | Medium | Last-write-wins strategy + audit log |

---

## Future Opportunities

- **Wearable Integration**: Smartwatch sensors, body cam footage
- **AI/ML**: Auto-categorization, face recognition, OCR
- **AR Visualization**: Overlay data on map/camera
- **Voice Commands**: Hands-free data collection
- **Advanced Sensors**: Thermal imaging, LiDAR, spectrum analysis
- **Third-Party Integrations**: Social media scrapers, public records APIs
- **Offline-First Architecture**: Full app functionality without internet
- **Desktop Sync**: Desktop client for investigation management

---

## Getting Started (For New Developers)

### Developer Prerequisites
- Android: Android Studio, Kotlin 1.8+, Gradle
- iOS: Xcode, Swift 5.5+, CocoaPods/SPM
- API: Basset Hound running locally or cloud instance
- Git: GitHub clone of basset-hound-mobile repo

### Quick Start
1. Clone repo: `git clone [repo-url] basset-hound-mobile`
2. Read `MOBILE-README.md` (project overview)
3. Read `docs/ARCHITECTURE.md` (technical design)
4. Read `docs/SETUP.md` (development environment)
5. Start with `docs/PHASE-1-MVP.md` for current sprint
6. Join Slack channel for team communication

### Code Structure
```
basset-hound-mobile/
├── android/           # Android Kotlin code
│   ├── app/
│   ├── data/          # Local storage, API client
│   ├── ui/            # Jetpack Compose screens
│   └── viewmodel/     # MVVM state management
├── ios/               # iOS Swift code (Phase 2+)
│   ├── App/
│   ├── Data/
│   ├── UI/
│   └── ViewModel/
├── shared/            # KMP shared code (if using)
├── docs/              # Design docs, guides
├── tests/             # Unit + integration tests
└── README.md
```

---

## Questions for Stakeholders

Before implementation:
1. Will app work with self-hosted Basset Hound instances or cloud-only?
2. Do we need support for specific phone models (e.g., ruggedized devices)?
3. What's the maximum offline queue size acceptable?
4. Should officers be able to work on multiple investigations simultaneously?
5. Do we need real-time collaboration (live updates) or async (sync on demand)?
6. What's the expected data volume per officer per day?
7. Should app work in airplane mode / no internet?
8. Do we need biometric unlock (fingerprint, face)?
9. Should officers be able to share investigations with other officers?
10. Is budget available for cloud storage for media files?

---

## Conclusion

Basset Hound Mobile transforms investigative work by turning officer phones into powerful field data collection instruments. Combined with the cloud-based Basset Hound platform, it enables law enforcement and private investigators to:

- Collect evidence in real-time
- Access device sensors for comprehensive data gathering
- Maintain secure chain of custody
- Collaborate across teams
- Sync findings to central investigation database
- Leverage advanced analytics on collected data

This creates a complete OSINT platform ecosystem: **Cloud backend (Basset Hound) + Mobile field tool (Basset Hound Mobile)**.

**Status**: Ready for team recruitment and Phase 1 implementation.

---

**Plan Created**: 2026-05-07  
**Plan Status**: SCOPE & ARCHITECTURE COMPLETE  
**Next Step**: Team assembly and Phase 1 implementation
