

# 🛰️ **SPACECLIP EXECUTION PLAN (HYBRID MODE — CONFIRMATION ON DANGEROUS TASKS)**

**Version:** 0.03
**Cursor Mode:** Hybrid
**Stop Frequency:** Only at `"requires: human-confirmation"`
**Global Model Default:** `auto` (Cursor rules will override)

---

## 📊 **PROGRESS SUMMARY**

**Phase 1 Progress:** 14/14 tasks completed (100%) ✅ **PHASE 1 COMPLETE!**
**Phase 2 Progress:** 2/2 tasks completed (100%) ✅ **PHASE 2 COMPLETE!**
**Phase 2.5 Progress:** 4/9 tasks completed (44%) - 4 auto tasks done, 5 require confirmation

**✅ Phase 1 Completed Tasks:**
- Task 1.1 — Fix user/project isolation
- Task 1.2 — Fix logout not clearing state
- Task 1.3 — Fix archive/delete 404
- Task 1.4 — Implement failure states
- Task 1.5 — Whisper long-form processing stalls
- Task 1.6 — Project queue status updates
- Task 1.7 — Transcript click-to-scrub bug
- Task 1.8 — Scrolling "stuck at bottom" bug
- Task 1.9 — Mobile dropdown invisible
- Task 1.10 — Project card overflow
- Task 1.11 — Select All alignment
- Task 1.12 — Audiogram template mismatch
- Task 1.13 — Duplicate clips on reanalysis
- Task 1.14 — Active/Archived toggle & Portal menu

**✅ Phase 2 Completed Tasks:**
- Task 2.1 — Drag handles for clip boundaries
- Task 2.2 — Regenerate captions after manual trim

**✅ Phase 2.5 Completed Tasks (Auto):**
- Task 2.5.1 — Project list state reconciliation ✅ **JUST COMPLETED**
- Task 2.5.3 — Relax and relocate clip boundary editor ✅ **JUST COMPLETED**
- Task 2.5.7 — Export preview correctness ✅ **JUST COMPLETED**
- Task 2.5.8 — Template visibility (read-only) ✅ **JUST COMPLETED**

**⏸️ Phase 2.5 Pending (Require Confirmation):**
- Task 2.5.2 — Fix clip time semantics (opus-4.5, confirmation required)
- Task 2.5.4 — Highlight timing alignment bug (opus-4.5, confirmation required)
- Task 2.5.5 — Improve highlight discovery quality (opus-4.5, confirmation required)
- Task 2.5.6 — Speaker name inference (opus-4.5, confirmation required)
- Task 2.5.9 — Auth surface cleanup (auto, confirmation required)

**📝 Next Up:**
- Complete remaining Phase 2.5 tasks (require confirmation)
- Phase 3 — Paywall + Invites (requires confirmation)

**📝 Notes:**
- Multi-tenant isolation fully implemented with user-scoped cache keys (`user_id:media_id`)
- All media operations now require authentication (`require_auth` dependency)
- Frontend API routes fixed to use correct endpoints
- Database setup scripts created for easier development (`scripts/setup-db.sh`, `scripts/dev.sh`, `scripts/kill.sh`)
- Active/Archived project views with restore functionality
- Portal-based dropdown menus prevent clipping issues
- Long-form audio processing with chunked transcription (10-min chunks)
- Real-time status polling for processing jobs (2s interval)
- Content-based duplicate detection for clips (SHA256 hashing)
- Drag handles for manual clip boundary adjustment with word-boundary snapping

**⚠️ Missing Documentation/Comments:**
- Some early tasks (1.1-1.4, 1.7-1.11) lack detailed file modification lists (completed in earlier sessions)
- Regression tests mentioned in Task 1.1 not yet implemented
- Toast feedback for archive/delete operations (Task 1.3) not yet implemented

---

# ================================

# **PHASE 1 — CORE STABILITY**

# ================================

### *Goal: make Spaceclip feel like it wasn’t designed by a ghost.*

---

## **TASK 1.1 — Fix user/project isolation** ✅ **COMPLETED**

```
model: opus-4.5
requires: human-confirmation
status: ✅ COMPLETED
```

**Actions:**

* ✅ Ensure all project queries require `user_id`
* ✅ Patch frontend stores to stop leaking previous user's state
* ⏸️ Add regression tests (not yet implemented - TODO)

**Implementation:**
- Changed cache key format from `media_id` to `user_id:media_id` for multi-tenancy
- Updated `_load_or_create_project()` to enforce ownership checks
- Added `user_id` and `project_id` fields to `ProjectState` schema
- All upload/process/delete endpoints now require `require_auth` dependency
- Frontend project store clears on logout to prevent state leakage

**Files Modified:**
- `backend/api/routes.py` - Cache key changes, ownership enforcement, `require_auth` on all endpoints
- `backend/models/schemas.py` - Added `user_id` and `project_id` to `ProjectState`
- `backend/services/project_storage.py` - User-scoped queries, ownership verification
- `frontend/src/store/project.ts` - Added `clearAll()` method for logout
- `frontend/src/components/layout/Header.tsx` - Calls `clearAll()` on logout

**Note:** Detailed file-by-file changes from earlier sessions not fully documented here.

---

## **TASK 1.2 — Fix logout not clearing state** ✅ **COMPLETED**

```
model: auto
status: ✅ COMPLETED
```

**Actions:**

* ✅ Clear all auth + project stores on logout
* ✅ Add redirect

**Implementation:**
- Added `clearAll()` method to project store that clears all state including recent projects
- Updated logout handler to call `clearAll()` before redirecting
- Ensures no cross-user state leakage on logout/login

**Files Modified:**
- `frontend/src/store/project.ts` - Added `clearAll()` method
- `frontend/src/components/layout/Header.tsx` - Updated `handleLogout` to clear state

---

## **TASK 1.3 — Fix archive/delete 404** ✅ **COMPLETED**

```
model: opus-4.5
requires: human-confirmation
status: ✅ COMPLETED
```

**Actions:**

* ✅ Validate backend route + verb
* ✅ Patch controller + repo
* ✅ Patch frontend call
* ⏸️ Add toast feedback (not yet implemented - TODO)

**Implementation:**
- Fixed route paths: `/projects/{media_id}/archive` (POST) and `/projects/{media_id}` (DELETE)
- Updated repository methods to accept `user_id` for ownership verification
- Fixed frontend API calls to use correct endpoints and HTTP methods
- Archive/unarchive operations now properly update media status in database

**Files Modified:**
- `backend/api/routes.py` - Fixed route definitions, added `require_auth`, user_id checks
- `backend/services/project_storage.py` - Updated `delete_project_async`, `archive_media`, `unarchive_media` with user_id
- `frontend/src/lib/api.ts` - Fixed `deleteProject`, `archiveProject`, `unarchiveProject` functions
- `frontend/src/components/projects/ProjectsModal.tsx` - Updated action handlers

**Note:** Toast notifications for success/error feedback not yet implemented.

---

## **TASK 1.4 — Implement failure states** ✅ **COMPLETED**

```
model: auto
status: ✅ COMPLETED
```

**Actions:**

* ✅ Upload error UI (already existed)
* ✅ Transcription error UI (already existed)
* ✅ Clip-generation error UI (already existed)
* ✅ Backend sends `status: ERROR` (implemented)

**Implementation:**
- Backend now sets `ProcessingStatus.ERROR` and `error` message on failures
- Frontend error handling displays user-friendly messages
- Processing view shows error state with retry option
- Error messages include context (timeout, network, etc.)

**Files Modified:**
- `backend/api/routes.py` - Error handling in processing endpoints sets ERROR status
- `frontend/src/components/processing/ProcessingView.tsx` - Error display and retry logic

---

## **TASK 1.5 — Whisper long-form processing stalls** ✅ **COMPLETED**

```
model: opus-4.5
requires: human-confirmation
status: ✅ COMPLETED
```

**Actions:**

* ✅ Introduce chunked processing pipeline (10-min chunks for >10 min audio)
* ✅ Retry + timeout logic (3 retries with exponential backoff)
* ✅ Progress events for UI (real-time callbacks during transcription)

**Implementation:**
- Audio files >10 minutes are automatically chunked into 10-minute segments
- Each chunk is transcribed separately with retry logic (up to 3 attempts)
- Segments are merged with overlap detection at chunk boundaries
- Progress callback system reports real-time updates to UI
- Uses ffmpeg for chunk extraction (WAV format, 16kHz mono)

**Files Modified:**
- `backend/services/transcription.py` - Chunked processing, retry logic, progress callbacks
- `backend/api/routes.py` - Progress callback integration in background processing

---

## **TASK 1.6 — Project queue status updates** ✅ **COMPLETED**

```
model: opus-4.5
requires: human-confirmation
status: ✅ COMPLETED
```

**Actions:**

* ✅ `/projects/{media_id}/status` endpoint (lightweight polling endpoint)
* ✅ Polling in FE (2s interval during processing)
* ✅ Job state transitions: `PENDING → DOWNLOADING → TRANSCRIBING → ANALYZING → COMPLETE | ERROR`

**Implementation:**
- New `ProjectStatusResponse` model with minimal fields for efficient polling
- Status endpoint checks in-memory cache first, then falls back to database
- Frontend polls every 2 seconds during processing
- Real-time status messages displayed in UI (e.g., "Transcribing chunk 2/5...")
- Automatic transition to highlights view on completion

**Files Modified:**
- `backend/models/schemas.py` - Added `ProjectStatusResponse` model, `status_message` field
- `backend/models/__init__.py` - Export new model
- `backend/api/routes.py` - New `/projects/{media_id}/status` endpoint
- `frontend/src/lib/api.ts` - Added `getProjectStatus()` function, updated types
- `frontend/src/components/processing/ProcessingView.tsx` - Status polling with 2s interval

---

## **TASK 1.7 — Transcript click-to-scrub bug** ✅ **COMPLETED**

```
model: auto
status: ✅ COMPLETED
```

**Actions:**

* ✅ Fix timestamp mapping
* ✅ Update player seek logic

**Implementation:**
- Fixed transcript segment click handler to correctly map to media time
- Updated MediaPlayer seek logic to handle transcript clicks
- Ensures accurate scrubbing when clicking transcript segments

**Files Modified:**
- `frontend/src/components/player/MediaPlayer.tsx` - Fixed `jumpToSegment()` method
- `frontend/src/components/highlights/TranscriptViewer.tsx` - Fixed click handler timestamp mapping

**Note:** Specific implementation details from earlier session not fully documented.

---

## **TASK 1.8 — Scrolling “stuck at bottom” bug**

```
model: auto
status: ✅ COMPLETED
```

**Actions:**

* ✅ Remove overflow locking
* ✅ Fix scroll restoration

**Implementation:**
- Removed CSS that was locking scroll position at bottom
- Fixed scroll restoration logic to preserve user's scroll position
- Prevents automatic scrolling to bottom on content updates

**Files Modified:**
- `frontend/src/components/highlights/TranscriptViewer.tsx` - Removed overflow locking, fixed scroll behavior

**Note:** Specific CSS/implementation details from earlier session not fully documented.

---

## **TASK 1.9 — Mobile dropdown invisible** ✅ **COMPLETED**

```
model: auto
status: ✅ COMPLETED
```

**Actions:**

* ✅ Raise z-index
* ✅ Fix pointer-events

**Implementation:**
- Increased z-index for dropdown menus to ensure visibility above other elements
- Fixed pointer-events CSS to allow proper interaction on mobile devices
- Ensures dropdowns are clickable and visible on touch devices

**Files Modified:**
- `frontend/src/components/layout/Header.tsx` - Increased z-index for user menu
- Various dropdown components - Fixed pointer-events and z-index

**Note:** Specific file changes from earlier session not fully documented.

---

## **TASK 1.10 — Project card overflow** ✅ **COMPLETED**

```
model: auto
status: ✅ COMPLETED
```

**Actions:**

* ✅ Truncate long titles
* ✅ Force wrapping
* ✅ Remove horizontal scroll

**Implementation:**
- Added text truncation for long project titles
- Applied CSS to force text wrapping within card boundaries
- Removed horizontal scroll from project list containers
- Ensures cards fit within layout without overflow

**Files Modified:**
- `frontend/src/components/projects/ProjectHistory.tsx` - Fixed card overflow and wrapping
- `frontend/src/components/projects/ProjectsModal.tsx` - Fixed modal container overflow

**Note:** Specific CSS changes from earlier session not fully documented.

---

## **TASK 1.11 — Select All alignment** ✅ **COMPLETED**

```
model: auto
status: ✅ COMPLETED
```

**Actions:**

* ✅ Align bulk-action bar with card container

**Implementation:**
- Fixed alignment of bulk action bar (Select All, Delete, Archive) with project card container
- Ensures consistent spacing and alignment across the UI
- Improved visual consistency in project list views

**Files Modified:**
- `frontend/src/components/projects/ProjectHistory.tsx` - Fixed bulk action bar alignment

**Note:** Specific CSS/alignment changes from earlier session not fully documented.

---

## **TASK 1.14 — Active/Archived Toggle & Portal Menu** ✅ **COMPLETED**

```
model: opus-4.5
status: ✅ COMPLETED
```

**Actions:**

* ✅ Add Active/Archived tabs to ProjectsModal
* ✅ Implement client-side filtering based on status
* ✅ Create reusable PortalMenu component (React portal)
* ✅ Fix dropdown menu clipping with position: fixed + z-index: 10000
* ✅ Add Restore action for archived projects
* ✅ Apply muted styling (opacity + grayscale) to archived cards
* ✅ Update API to support `include_archived` parameter
* ✅ Menu closes on click outside and ESC key
* ✅ Menu positions correctly on scroll/resize

**Files Modified:**
- `frontend/src/lib/api.ts` - Added `includeArchived` parameter
- `frontend/src/components/ui/PortalMenu.tsx` - New reusable portal component
- `frontend/src/components/projects/ProjectsModal.tsx` - Complete UI overhaul

---

## **TASK 1.12 — Audiogram template mismatch** ✅ **COMPLETED**

```
model: auto
status: ✅ COMPLETED
```

**Actions:**

* ✅ Sync template UI + ffmpeg output template
* ✅ Updated frontend colors to match backend:
  - Cosmic: `#0f0a1f` background, `#a855f7` waveform
  - Neon: `#00ffff` waveform
  - Sunset: `#ff6b6b` waveform
  - Minimal: `#333333` waveform
* ✅ Removed unsupported themes (ocean, forest) from frontend

**Files Modified:**
- `frontend/src/components/audiogram/AudiogramCustomizer.tsx` - Synced theme colors

---

## **TASK 1.13 — Duplicate clips on reanalysis** ✅ **COMPLETED**

```
model: opus-4.5
status: ✅ COMPLETED
```

**Actions:**

* ✅ Add hashing for (start, end, platform, media_id, captions_text)
* ✅ Generate deterministic clip IDs from content hash
* ✅ Prevent duplicate DB writes by checking existing clips
* ✅ Return existing clip if duplicate detected instead of creating new one

**Implementation:**
- `_generate_clip_hash()` - Creates SHA256 hash from clip characteristics
- `_get_captions_text()` - Extracts text content for hashing
- Updated `create_clip()` to accept `existing_clips` for duplicate checking
- Updated `/clips` endpoint to check duplicates before creation
- Updated background processing to check duplicates

**Files Modified:**
- `backend/services/clip_generator.py` - Added hash generation and duplicate checking
- `backend/api/routes.py` - Added duplicate checking in create_clips endpoint

---

# ================================

# **PHASE 2 — MANUAL CLIP CONTROLS** ✅ **COMPLETE**

# ================================

---

## **TASK 2.1 — Drag handles for clip boundaries** ✅ **COMPLETED**

```
model: opus-4.5
requires: human-confirmation
status: ✅ COMPLETED
```

**Actions:**

* ✅ Add draggable handles to timeline
* ✅ Word-boundary snapping (snaps to transcript segment boundaries)
* ✅ Save new positions to DB

**Implementation:**
- Created `ClipRangeEditor` component with:
  - Drag handles at start/end of clip region
  - Visual timeline with clip region highlight
  - Word-boundary snapping (0.5s threshold)
  - Tooltips showing current time during drag
  - Duration constraints (5s min, 180s max)
  - Touch support for mobile
- Integrated into `ExportView` for clip adjustment before export
- Added `POST /projects/{media_id}/clip-range` endpoint for saving

**Files Created/Modified:**
- `frontend/src/components/player/ClipRangeEditor.tsx` (NEW) - Complete drag handle implementation
- `frontend/src/components/export/ExportView.tsx` - Integrated ClipRangeEditor, added range commit handler
- `backend/api/routes.py` - Added `POST /projects/{media_id}/clip-range` endpoint
- `frontend/src/lib/api.ts` - Added `updateClipRange()` API function

---

## **TASK 2.2 — Regenerate captions after manual trim** ✅ **COMPLETED**

```
model: opus-4.5
requires: human-confirmation
status: ✅ COMPLETED
```

**Actions:**

* ✅ Whisper segment slicing (filter by time range)
* ✅ Rebuild caption track (adjust timestamps relative to clip start)
* ✅ Resync with video output (captions regenerated on export)

**Implementation:**
- `GET /projects/{media_id}/captions` endpoint:
  - Takes start/end time range
  - Filters transcript segments overlapping range
  - Adjusts timestamps relative to clip start
  - Returns ready-to-use caption data
- `POST /projects/{media_id}/clip-range` endpoint:
  - Validates time range
  - Returns updated captions for new range
  - Associates with highlight if provided
- Frontend updates captions when clip boundaries change

**Files Modified:**
- `backend/api/routes.py` - Added `GET /projects/{media_id}/captions` and `POST /projects/{media_id}/clip-range` endpoints
- `frontend/src/lib/api.ts` - Added `getClipCaptions()` and `updateClipRange()` functions, type definitions
- `frontend/src/components/export/ExportView.tsx` - Added caption update handling, displays caption count
- `frontend/src/components/player/ClipRangeEditor.tsx` - Added `onRangeCommit` callback for saving changes

---

## 🔧 **PHASE 2.5 — TRUST, INTELLIGENCE & FLOW** *(NEW)*

> *Goal: make Spaceclip feel competent, predictable, and worth trusting.*
## ⚠️ Phase 2.5 Clarification: Trust-Critical Systems

The following systems are considered **trust-critical**.
They must prioritize correctness, transparency, and predictability over speed or polish:

- Processing progress UI
- Highlight discovery feedback
- Clip timestamp display

For trust-critical systems:
- Do NOT display percentages unless derived from real, countable progress
- Do NOT reuse placeholder defaults (e.g. 15s) once real data exists
- Do NOT collapse multi-stage processes into a single ambiguous state

If accuracy cannot be guaranteed, the UI must say so explicitly.


---

### **TASK 2.5.1 — Project list state reconciliation** ✅ **COMPLETED**

```
model: auto
status: ✅ COMPLETED
```

**Problem:**
Archived / unarchived projects do not immediately appear or disappear without a full page refresh.

**Actions:**

* ✅ Invalidate or refetch project list after:

  * archive
  * unarchive
  * delete
* ✅ Implement optimistic UI updates with fallback refetch on failure
* ✅ Ensure Active / Archived tabs stay in sync with backend state

**Implementation:**
- Added optimistic UI updates that immediately reflect changes
- Refetch project list after successful operations to ensure sync
- Revert optimistic updates on failure, then refetch to get correct state
- Applied to both ProjectsModal and ProjectHistory components
- Works for single and bulk operations

**Files Modified:**
- `frontend/src/components/projects/ProjectsModal.tsx` - Added refetch logic to archive/unarchive/delete handlers
- `frontend/src/components/projects/ProjectHistory.tsx` - Added refetch logic to all action handlers

**Impact:**
Restores user trust in basic project management actions.

**Why auto:**
- Straightforward state management and API refetching
- No data model changes or complex logic required

---

### **TASK 2.5.2 — Fix clip time semantics**

```
model: opus-4.5
requires: human-confirmation
status: ⏳ PLANNED
⚠️ EXECUTION REQUIREMENT:
This task must be executed in a fresh context using opus-4.5.
If the active model is not opus-4.5, STOP and ask for confirmation.
```

**Problem:**
Clips display incorrect timestamps (e.g. `0:00–0:15`) even when the clip occurs later in the source media.

**Actions:**

* Normalize clip data model:

  * Store **absolute media timestamps** for clips
  * Derive relative timestamps only for export/render
* Update UI to display true `start → end` times
* Remove hard-coded 15s assumptions across clip UI
* **Migration strategy**: Handle existing clips with relative timestamps

**Impact:**
Fixes a major credibility issue and aligns UI with actual media behavior.

**Why opus-4.5 + confirmation:**
- Changes core data model (absolute vs relative timestamps)
- Requires migration strategy for existing clips
- Could break existing exports/clips if not handled carefully

---

### **TASK 2.5.3 — Relax and relocate clip boundary editor** ✅ **COMPLETED**

```
model: auto
status: ✅ COMPLETED
```

**Problem:**
Clip boundary editing is constrained (3 min max) and placed too late in the flow (Export).

**Actions:**

* ✅ Move clip boundary editing to **Select / Edit** stage (HighlightsView)
* ✅ Remove or relax 3-minute hard cap (now `undefined` = no limit)
* ✅ Allow independent dragging of start and end handles across timeline
* ✅ Preserve word-boundary snapping behavior

**Implementation:**
- Moved `ClipRangeEditor` from ExportView to HighlightsView (Select/Edit stage)
- Changed `maxClipDuration` from 180s to `undefined` (no maximum limit)
- ExportView now shows read-only clip range display
- Clip range changes are saved to backend via `updateClipRange` API
- Editor automatically saves changes when drag ends

**Files Modified:**
- `frontend/src/components/player/ClipRangeEditor.tsx` - Made maxClipDuration optional (undefined = no limit)
- `frontend/src/components/highlights/HighlightsView.tsx` - Added ClipRangeEditor integration
- `frontend/src/components/export/ExportView.tsx` - Removed editor, shows read-only range display

**Impact:**
Restores creative control and aligns with user mental model.

**Why auto:**
- UI component relocation and constraint removal
- No data model or backend changes required

---

### **TASK 2.5.4 — Highlight timing alignment bug**

```
model: opus-4.5
requires: human-confirmation
status: ⏳ PLANNED
⚠️ EXECUTION REQUIREMENT:
This task must be executed in a fresh context using opus-4.5.
If the active model is not opus-4.5, STOP and ask for confirmation.
```

**Problem:**
Some highlights default to the start of the source media instead of their true position.

**Actions:**

* Validate highlight timestamps at creation time
* Ensure highlight offsets correctly map to absolute media timeline
* Add sanity checks before clip generation
* **Data integrity**: Fix existing highlights with invalid timestamps

**Impact:**
Prevents invalid clips and downstream export errors.

**Why opus-4.5 + confirmation:**
- Fixes core data integrity issue affecting highlights
- Requires validation logic and potentially data migration
- Could affect existing projects with bad highlight data

---

### **TASK 2.5.5 — Improve highlight discovery quality**

**Dependency:**
This task assumes Task 2.5.10 (Processing transparency) is complete,
so users can distinguish between “still analyzing” and “analysis complete but conservative.”

```
model: opus-4.5
requires: human-confirmation
⚠️ EXECUTION REQUIREMENT:
This task must be executed in a fresh context using opus-4.5.
If the active model is not opus-4.5, STOP and ask for confirmation.
status: ⏳ PLANNED
```

**Problem:**
Highlight generation is overly conservative and often returns too few results, especially for long-form content.

**Actions:**

* Introduce minimum highlight density heuristic (e.g. 5–10 per hour)
* Apply diversity constraints to avoid clustering
* Replace hard thresholds with re-ranking + scoring
* Use combined signals:

  * transcript content
  * sentiment shifts
  * speaker turns
  * emphasis markers

**Impact:**
Produces consistently useful highlights instead of “lucky hits.”

---

### **TASK 2.5.6 — Speaker name inference**

```
model: opus-4.5
requires: human-confirmation
⚠️ EXECUTION REQUIREMENT:
This task must be executed in a fresh context using opus-4.5.
If the active model is not opus-4.5, STOP and ask for confirmation.
status: ⏳ PLANNED
```

**Problem:**
Transcript speaker labels are generic (Speaker 1 / Speaker 2) even when names are clearly stated in context.

**Actions:**

* Detect self-identification phrases (“I’m Tony…”, “This is Zach…”)
* Map recurring speakers to inferred names when confidence is high
* Persist speaker mapping per project
* Fall back safely to generic labels when uncertain
* Never hallucinate speaker names

**Impact:**
Massively improves transcript readability and highlight quality.

**Why opus-4.5 + confirmation:**
- NLP/pattern matching logic requiring careful implementation
- Must never hallucinate names - requires strict confidence thresholds
- Affects transcript quality - needs validation before deployment

---

### **TASK 2.5.7 — Export preview correctness**

```
model: auto
status: ⏳ PLANNED
```

**Problem:**
Export previews do not reliably reflect selected platforms or caption settings.

**Actions:**

* Render previews for **all selected platforms** simultaneously
* Persist last-used export platforms per user
* Ensure “Include captions” is reflected in preview output

**Impact:**
Aligns preview expectations with final export results.

**Implementation:**
- Updated `ClipPreview` component to accept `platform` and `showCaptions` props
- Added platform specs for correct aspect ratios (9:16, 16:9, 1:1)
- Renders separate preview for each selected platform
- Shows caption overlay when `includeCaption` is enabled
- Captions are filtered and timestamp-adjusted for the clip range
- Last-used platforms persist in Zustand store (already persisted to localStorage)

**Files Modified:**
- `frontend/src/components/export/ExportView.tsx` - Multiple preview rendering, caption display
- `frontend/src/store/project.ts` - Added `setSelectedPlatforms` method for persistence

**Why auto:**
- UI rendering and state persistence logic
- No complex algorithms or data model changes

---

### **TASK 2.5.8 — Template visibility (read-only)** ✅ **COMPLETED**

```
model: auto
status: ✅ COMPLETED
```

**Problem:**
Users cannot see all available export templates to assess quality or consistency.

**Actions:**

* ✅ Add read-only template gallery
* ✅ Show all available export templates
* ✅ No editing or customization yet

**Implementation:**
- Created `TemplateGallery` component with visual previews
- Shows all 4 templates (Cosmic, Neon, Sunset, Minimal)
- Each template shows:
  - Color scheme preview with waveform visualization
  - Progress bar preview
  - Template name and description
- Read-only mode (no selection/editing)
- Integrated into ExportView for audio media

**Files Created/Modified:**
- `frontend/src/components/export/TemplateGallery.tsx` (NEW) - Read-only template gallery
- `frontend/src/components/export/ExportView.tsx` - Added TemplateGallery integration

**Impact:**
Prepares groundwork for branded templates without increasing scope.

---

### **TASK 2.5.9 — Auth surface cleanup**

```
model: auto
requires: human-confirmation
status: ⏳ PLANNED
```

**Problem:**
Multiple auth options reduce perceived trust and increase surface area.

**Actions:**

* Hide Google / Apple / Wallet login options
* Email-only authentication for now
* **Preserve backend**: Keep OAuth providers in code but hide from UI
* **Analytics**: Track impact on signup conversion

**Impact:**
Simplifies onboarding and improves enterprise trust perception.

**Why confirmation needed:**
- Significant UX/product decision affecting user onboarding
- Should confirm with stakeholders before removing auth options
- May impact signup rates - needs monitoring

---

### **TASK 2.5.10 — Processing transparency (trust-critical)**

model: auto
status: ⏳ PLANNED

**Problem:**
Processing UI displays misleading percent-based progress that does not reflect real backend state, causing users to believe the app is stalled or inaccurate.

**Actions:**

* Replace percentage-based progress with **stage-based indicators**
* Display:
  - Current stage: downloading | chunking | transcribing | analyzing | highlighting
  - Chunk progress: `chunk X / Y` when applicable
* If progress cannot be quantified, show indeterminate state (“Working…”) explicitly
* Ensure UI state is derived directly from `/projects/{media_id}/status`

**Hard rules:**
- ❌ No fake percentages
- ❌ No smoothing or interpolation
- ✅ Only show what the system actually knows

**Exit criteria:**
- Terminal logs and UI state tell the same story
- Users never see “stuck at 65%” again


---

## 📋 **Phase 2.5 Model & Confirmation Summary**

### **Tasks Using `auto` Model (No Confirmation Required):**
- **2.5.1** - Project list state reconciliation (UI state management)
- **2.5.3** - Relax and relocate clip boundary editor (UI component relocation)
- **2.5.7** - Export preview correctness (UI rendering logic)
- **2.5.8** - Template visibility (read-only UI gallery)

### **Tasks Using `opus-4.5` Model (Requires Human Confirmation):**
- **2.5.2** - Fix clip time semantics ⚠️ **CONFIRMATION REQUIRED**
  - Changes core data model (absolute vs relative timestamps)
  - Requires migration strategy for existing clips
- **2.5.4** - Highlight timing alignment bug ⚠️ **CONFIRMATION REQUIRED**
  - Fixes data integrity issue affecting highlights
  - May require data migration
- **2.5.5** - Improve highlight discovery quality ⚠️ **CONFIRMATION REQUIRED**
  - Complex AI/ML algorithm changes
  - Affects core highlight quality
- **2.5.6** - Speaker name inference ⚠️ **CONFIRMATION REQUIRED**
  - NLP/pattern matching logic
  - Must never hallucinate names

### **Tasks Using `auto` Model (But Requires Confirmation):**
- **2.5.9** - Auth surface cleanup ⚠️ **CONFIRMATION REQUIRED**
  - Significant UX/product decision
  - May impact signup conversion rates

**Note:** Tasks 2.5.2, 2.5.4, 2.5.5, 2.5.6, and 2.5.9 all require human confirmation before execution due to their impact on data integrity, core functionality, or user experience.

---

## ✅ Phase 2.5 Exit Criteria

Phase 2.5 is considered complete when:

* Clip timestamps are accurate and trustworthy
* Highlights appear consistently across long-form content
* Speaker labels are human-readable when possible
* Project state updates feel immediate
* Export previews match final output

---

⚠️ Phase 3 (Paywall + Invites) must not begin until Phase 2.5 exit criteria are met.
Monetization should only be introduced once highlight quality, clip timing,
and export previews are consistently trustworthy.


# ================================

# **PHASE 3 — PAYWALL + INVITES**

# ================================

---

## **TASK 3.1 — Stripe checkout + billing portal**

```
model: opus-4.5
requires: human-confirmation
```

**Actions:**

* Create checkout session
* Handle webhook entitlement updates
* Sync plan to DB

---

## **TASK 3.2 — Feature gating**

```
model: opus-4.5
requires: human-confirmation
```

**Actions:**

* Free tier limits
* Watermark enforcement
* 720p cap
* Paid tier unlocks

---

## **TASK 3.3 — Founding Member Lifetime Deal**

```
model: opus-4.5
requires: human-confirmation
```

**Actions:**

* Create Stripe price
* `plan = lifetime_pro` entitlement

---

## **TASK 3.4 — Invite code system (full, limited, waitlist)**

```
model: opus-4.5
requires: human-confirmation
```

**Backend:**

* Create `invite_codes` + `user_invites`
* Redeem endpoint
* Invite-type → plan override logic
* Enforcement middleware

**Frontend** *(auto)*:

* “Enter invite code” modal
* Invite badge in settings
* Block features when missing invite

---

# ================================

# **PHASE 4 — HYBRID ENGINE**

# ================================

---

## **TASK 4.1 — Online/offline privacy toggle**

```
model: opus-4.5
requires: human-confirmation
```

**Actions:**

* Add FE toggle
* Job router chooses local vs cloud
* Provider fallback safety

---

## **TASK 4.2 — Provider switcher (Local / Venice / OpenAI)**

```
model: opus-4.5
requires: human-confirmation
```

**Actions:**

* Provider abstraction layer
* Error fallback
* Update config

---

## **TASK 4.3 — Local storage meter**

```
model: auto
```

**Actions:**

* Compute usage
* List stale projects
* Cleanup button

---

# ================================

# **PHASE 5 — CREATOR FEATURES**

# ================================

---

## **TASK 5.1 — User-defined highlights**

```
model: auto
```

## **TASK 5.2 — Background music**

```
model: auto
```

## **TASK 5.3 — Basic transitions**

```
model: auto
```

---

# ================================

# **PHASE 6 — ADVANCED CONTENT**

# ================================

---

## **TASK 6.1 — Text-to-audiogram**

```
model: opus-4.5
requires: human-confirmation
```

## **TASK 6.2 — Talking avatar templates**

```
model: opus-4.5
requires: human-confirmation
```

---

# ================================

# **PHASE 7 — PLATFORM EXPANSION**

# ================================

---

## **TASK 7.1 — Model marketplace**

```
model: opus-4.5
requires: human-confirmation
```

## **TASK 7.2 — Enterprise on-prem**

```
model: opus-4.5
requires: human-confirmation
```

## **TASK 7.3 — GPU DePIN (future)**

```
model: opus-4.5
requires: human-confirmation
```

---

# 🧠 Cursor Execution Notes

Cursor will:

### ✔ Run tasks **in order**

### ✔ Pick the right model for each task

### ✔ Stop only when `"requires: human-confirmation"` is present

### ✔ Obey your `.cursor/rules.json` (auth/env safety fences)

### ✔ Not rewrite your auth system

### ✔ Not mutate env schema

### ✔ Not generate migrations without confirmation

### ✔ Not alter billing/invite logic without approval

In other words: it behaves.

---

# 📋 **COMPREHENSIVE IMPLEMENTATION SUMMARY**

## **Phase 1: Core Stability (14/14 tasks) ✅**

### **Architecture & Security**
- **Multi-tenant isolation**: All cache keys use `user_id:media_id` format
- **Authentication**: All media/project endpoints require `require_auth` dependency
- **State management**: Frontend stores properly clear on logout to prevent cross-user leakage
- **Database**: User-scoped queries throughout, ownership verification on all operations

### **Processing & Performance**
- **Long-form transcription**: Chunked processing (10-min segments) with retry logic (3 attempts, exponential backoff)
- **Status polling**: Lightweight `/status` endpoint with 2s polling interval
- **Progress tracking**: Real-time callbacks during transcription with detailed status messages
- **Duplicate prevention**: Content-based hashing (SHA256) prevents duplicate clips on reanalysis

### **UI/UX Improvements**
- **Archive system**: Active/Archived toggle with restore functionality
- **Portal menus**: React portal-based dropdowns prevent clipping issues
- **Template sync**: Frontend audiogram colors match backend ffmpeg output
- **Bug fixes**: Transcript scrubbing, scroll behavior, mobile dropdowns, card overflow, alignment

## **Phase 2: Manual Clip Controls (2/2 tasks) ✅**

### **Clip Editing**
- **Drag handles**: Visual timeline with draggable start/end handles
- **Word-boundary snapping**: Automatically snaps to transcript segment boundaries (0.5s threshold)
- **Duration constraints**: 5s minimum, 180s maximum with visual feedback
- **Touch support**: Full mobile/touch device support

### **Caption Regeneration**
- **Automatic updates**: Captions regenerate when clip boundaries change
- **Timestamp adjustment**: Converts absolute timestamps to clip-relative timestamps
- **Segment filtering**: Only includes segments overlapping the clip range
- **API endpoints**: `GET /captions` and `POST /clip-range` for caption management

## **Key Technical Decisions**

1. **Cache Strategy**: In-memory cache with database persistence, user-scoped keys prevent cross-contamination
2. **Processing Strategy**: Chunked transcription for long-form content, background tasks with progress callbacks
3. **Duplicate Detection**: Deterministic UUIDs from content hash, checked before DB write
4. **UI Architecture**: React portals for dropdowns, Zustand for state management, Framer Motion for animations

## **Development Tools Created**

- `scripts/setup-db.sh` - Automated PostgreSQL setup and migrations
- `scripts/dev.sh` - Enhanced startup with dependency checks
- `scripts/kill.sh` - Clean process termination
- `QUICKSTART.md` - Streamlined development guide

## **Known Limitations / TODOs**

- ⏸️ Regression tests for user isolation (Task 1.1)
- ⏸️ Toast notifications for archive/delete operations (Task 1.3)
- ⏸️ Some early tasks lack detailed file modification documentation (completed in earlier sessions)

---

# Want me to generate:

### ✅ A version formatted specifically for `/cursor/tasks.json`

### ✅ A clickable task tree to drive Cursor’s task runner

### ✅ A PR template Cursor uses for each automated change

### ✅ A shell script to run each “dangerous” task in isolation

Just ask.
