

# 🛰️ **SPACECLIP EXECUTION PLAN (HYBRID MODE — CONFIRMATION ON DANGEROUS TASKS)**

**Version:** 0.03
**Cursor Mode:** Hybrid
**Stop Frequency:** Only at `"requires: human-confirmation"`
**Global Model Default:** `auto` (Cursor rules will override)

---

## 📊 **PROGRESS SUMMARY**

**Phase 1 Progress:** 9/13 tasks completed (69%)

**✅ Completed Tasks:**
- Task 1.1 — Fix user/project isolation
- Task 1.2 — Fix logout not clearing state
- Task 1.3 — Fix archive/delete 404
- Task 1.4 — Implement failure states
- Task 1.7 — Transcript click-to-scrub bug
- Task 1.8 — Scrolling "stuck at bottom" bug
- Task 1.9 — Mobile dropdown invisible
- Task 1.10 — Project card overflow
- Task 1.11 — Select All alignment

**⏸️ Remaining Tasks:**
- Task 1.5 — Whisper long-form processing stalls (requires confirmation)
- Task 1.6 — Project queue status updates (requires confirmation)
- Task 1.12 — Audiogram template mismatch
- Task 1.13 — Duplicate clips on reanalysis

**📝 Notes:**
- Multi-tenant isolation fully implemented with user-scoped cache keys
- All media operations now require authentication
- Frontend API routes fixed to use correct endpoints
- Database setup scripts created for easier development

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
* ⏸️ Add regression tests (not yet implemented)

---

## **TASK 1.2 — Fix logout not clearing state** ✅ **COMPLETED**

```
model: auto
status: ✅ COMPLETED
```

**Actions:**

* ✅ Clear all auth + project stores on logout
* ✅ Add redirect

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
* ⏸️ Add toast feedback (not yet implemented)

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

---

## **TASK 1.5 — Whisper long-form processing stalls**

```
model: opus-4.5
requires: human-confirmation
```

**Actions:**

* Introduce chunked processing pipeline
* Retry + timeout logic
* Progress events for UI

---

## **TASK 1.6 — Project queue status updates**

```
model: opus-4.5
requires: human-confirmation
```

**Actions:**

* `/projects/status` endpoint
* Polling in FE (2s)
* Job state transitions: `PENDING → PROCESSING → DONE → FAILED`

---

## **TASK 1.7 — Transcript click-to-scrub bug** ✅ **COMPLETED**

```
model: auto
status: ✅ COMPLETED
```

**Actions:**

* ✅ Fix timestamp mapping
* ✅ Update player seek logic

---

## **TASK 1.8 — Scrolling “stuck at bottom” bug**

```
model: auto
```

**Actions:**

* Remove overflow locking
* Fix scroll restoration

---

## **TASK 1.9 — Mobile dropdown invisible** ✅ **COMPLETED**

```
model: auto
status: ✅ COMPLETED
```

**Actions:**

* ✅ Raise z-index
* ✅ Fix pointer-events

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

---

## **TASK 1.11 — Select All alignment** ✅ **COMPLETED**

```
model: auto
status: ✅ COMPLETED
```

**Actions:**

* ✅ Align bulk-action bar with card container

---

## **TASK 1.12 — Audiogram template mismatch**

```
model: auto
```

**Actions:**

* Sync template UI + ffmpeg output template

---

## **TASK 1.13 — Duplicate clips on reanalysis**

```
model: opus-4.5
```

**Actions:**

* Add hashing for (start, end, text)
* Prevent duplicate DB writes

---

# ================================

# **PHASE 2 — MANUAL CLIP CONTROLS**

# ================================

---

## **TASK 2.1 — Drag handles for clip boundaries**

```
model: opus-4.5
requires: human-confirmation
```

**Actions:**

* Add draggable handles to timeline
* Word-boundary snapping
* Save new positions to DB

---

## **TASK 2.2 — Regenerate captions after manual trim**

```
model: opus-4.5
requires: human-confirmation
```

**Actions:**

* Whisper segment slicing
* Rebuild caption VTT track
* Resync video output

---

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

# Want me to generate:

### ✅ A version formatted specifically for `/cursor/tasks.json`

### ✅ A clickable task tree to drive Cursor’s task runner

### ✅ A PR template Cursor uses for each automated change

### ✅ A shell script to run each “dangerous” task in isolation

Just ask.
