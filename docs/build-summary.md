# OSLO POC Build Summary
**Sprint:** 9-day POC (Apr 15–23, 2026)
**Deadline:** May 2, 2026 (non-negotiable)
**Status:** Feature-complete, pending APK build

---

## Backend (oslo-api)

### Stack
- FastAPI + SQLAlchemy 2.0 + asyncpg
- Supabase Mumbai (PostgreSQL 15 + pgvector)
- Alembic migrations
- Dev-mode auth bypass (DEMO_OWNER_ID)

### Routes: 40 endpoints
| Group | Endpoints | Description |
|-------|-----------|-------------|
| Auth | 5 | dev-create, OTP send/verify, refresh, logout, delete |
| Profiles | 5 | CRUD + emergency profile |
| Consents | 3 | list, create, revoke |
| Documents | 7 | upload, finalize (classify→extract→denormalize), list, counts, detail, correct, explain, compare |
| Timeline | 4 | list (with filters), text note, voice note, summarize |
| Trends | 2 | lab value time series (system-grouped), available tests |
| Smart Report | 2 | AI-synthesized report (24h cache), active medications |
| Ask AI | 1 | question answering with patient records context |
| Wearable | 2 | Health Connect sync, wearable trends |
| Health | 1 | health check |

### AI Service
- `ai_service.py` — HTTP client calling XQZ's endpoints
- `ai_service_mock.py` — comprehensive mock with 12 Indian lab tests, 3 medications
- Auto-fallback: when `AI_SERVICE_BASE_URL` is empty, mock service activates
- Functions: classify, extract, explain, ask, summarize, transcribe, embed, check_health

### Database
- 2 Alembic migrations (001_initial_schema, 002_poc_additions)
- Tables: owner, profile, consent, document, extraction, lab_value, prescription, timeline_event, wearable_reading, smart_report_cache
- RLS on all tables via `oslo.current_owner_id`
- pgvector for document embeddings

### Commits: 10 on main

---

## Mobile (oslo-mobile)

### Stack
- React Native Expo SDK 52
- Expo Router (file-based routing)
- Zustand + AsyncStorage (state persistence)
- TypeScript (zero errors)

### Screens: 15
| Screen | Route | Features |
|--------|-------|----------|
| Home | /(tabs)/home | Greeting, quick actions, recent activity, values to watch, Smart Report CTA |
| Timeline | /(tabs)/timeline | FlatList, filter chips, search, add note button |
| Records | /(tabs)/records | Category rows with counts |
| Trends | /(tabs)/trends | MetricCard grid, sparklines, system filter chips |
| Ask AI | /(tabs)/ask | Chat UI, citations, refusal handling, suggested questions |
| Upload Review | /upload/review | Full pipeline: create→finalize→review→save |
| Document Detail | /document/[id] | Lab values table, prescription list, explain button |
| Records Filter | /records/[category] | Filtered document list by category |
| Smart Report | /smart-report | System cards, expandable values, PDF share |
| Emergency | /emergency | Pre-populated demo profile, allergies, conditions |
| Subscribe | /subscribe | ₹199/month plan, simulated Razorpay checkout |
| Settings | /settings | Profile edit, demo controls, privacy placeholders |
| Add Note | /timeline/add-note | Text + voice mode toggle |
| Splash/Index | / | Auto-init demo user, redirect to home |
| Layout | _layout | OfflineBanner, tab navigation |

### Components: 17
ProfileAvatar, StatusDot, StatusPill, SectionHeader, FilterChip, CategoryRow, AIDisclaimer, TabBar, QuickAction, ExtractionReview, CriticalValueBanner, Sparkline, VoiceRecorder, OfflineBanner, OnboardingTooltip, design-tokens, index barrel

### Tests: 12 suites, 26 tests, 25 snapshots — ALL PASSING

### Commits: 11 on main

---

## POC Capabilities Coverage (29/29 specified)

| # | Capability | Status |
|---|-----------|--------|
| 1 | Upload lab report (file picker) | ✅ |
| 2 | Camera scan (multi-page) | ⏳ Needs native build |
| 3 | Share intent (receive from gallery) | ⏳ Needs native build |
| 4 | AI classification | ✅ (mock + real endpoint ready) |
| 5 | AI extraction (structured data) | ✅ |
| 6 | Home tab (greeting, quick actions, recent, flagged) | ✅ |
| 7 | Timeline tab (events, filters, search) | ✅ |
| 8 | Records tab (category counts, filtered lists) | ✅ |
| 9 | Trends tab (sparklines, system filters) | ✅ |
| 10 | Ask AI tab (chat, citations, refusals) | ✅ |
| 11 | Smart Report (AI synthesis, system cards) | ✅ |
| 12 | Timeline text notes | ✅ |
| 13 | Timeline voice notes | ✅ |
| 14 | Timeline summarize | ✅ |
| 15 | Document explain | ✅ |
| 16 | Document compare (previous report diff) | ✅ |
| 17 | User correction (append-only) | ✅ |
| 18 | Lab value denormalization | ✅ |
| 19 | Prescription extraction | ✅ |
| 20 | Active medications list | ✅ |
| 21 | Wearable sync (Health Connect) | ⏳ Needs native build |
| 22 | Wearable trends | ✅ (API ready) |
| 23 | Emergency profile | ✅ |
| 24 | PDF share (doctor-presentable) | ✅ |
| 25 | Subscribe screen (₹199/month) | ✅ |
| 26 | Settings (profile, demo controls) | ✅ |
| 27 | Offline banner | ✅ |
| 28 | Onboarding tooltips | ✅ (Home, Timeline, Trends) |
| 29 | Demo data seeder (5 realistic reports) | ✅ |

**Score: 26/29 complete in code, 3 pending native module installation (EAS build)**

---

## Next Steps to APK

```bash
# 1. Install EAS CLI
npm install -g eas-cli

# 2. Login to Expo
eas login

# 3. Build preview APK
cd oslo-mobile
eas build --platform android --profile preview

# 4. Download APK from EAS dashboard
# 5. Sideload on Android device for demo
```

## External Dependencies
- [ ] XQZ AI endpoint URL → swap `AI_SERVICE_BASE_URL` in .env
- [ ] XQZ demo-reports.zip → replace synthetic seed data
- [ ] Pre-recorded screen recording → demo fallback
