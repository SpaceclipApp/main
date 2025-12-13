# Clip Timeline Architecture

## Core Principle: Clips as Views

**A clip is not its own canonical timeline. It is a window into the source media timeline.**

This fundamental framing explains why relative timestamps do not belong in storage and why absolute timestamps are used throughout the system.

---

## Why Clip Ranges Use Absolute Timestamps

### Current Architecture

1. **Highlights (database)**: `start_time` and `end_time` are **absolute** (seconds from media start)
   - Example: `start_time: 125.5, end_time: 140.2` means 2:05.5 to 2:20.2 in the source media

2. **Transcript segments (database)**: `start_time` and `end_time` are **absolute**
   - Example: `start_time: 120.0, end_time: 125.5` maps directly to the source media timeline

3. **Clip ranges (frontend/API)**: Passed as **absolute** timestamps
   - Example: `{ start: 125.5, end: 140.2 }` references the source media timeline

### Why Absolute Timestamps?

1. **Single Source of Truth**
   - One transcription serves all clips from the same media
   - Highlights reference the original media timeline
   - No ambiguity about which timeline is being used

2. **Query Efficiency**
   - Easy to ask "what happens at 5:30 in the original?"
   - Can filter segments: `WHERE start_time >= clip_start AND end_time <= clip_end`
   - No need to track which clip a relative timestamp belongs to

3. **Multiple Clips from One Media**
   - Multiple clips can reference the same source without coupling
   - Relative timestamps would require storing a `clip_id` reference, creating unnecessary coupling

4. **Media Player Compatibility**
   - Players expect absolute timestamps for seeking
   - `video.currentTime = 125.5` seeks to 2:05.5 in the source

5. **Data Integrity**
   - If a clip is deleted, the transcription/highlights remain valid
   - No cascading updates needed

---

## How Caption Rebasing Works

Caption rebasing converts **absolute timestamps** to **relative (0-based)** timestamps for export.

### The Process

1. **Input**: Absolute clip range
   ```python
   clip_start = 125.5  # Absolute: 2:05.5 in source media
   clip_end = 140.2    # Absolute: 2:20.2 in source media
   ```

2. **Filter Overlapping Segments**
   ```python
   # From transcription (absolute timestamps)
   segment.start = 120.0  # Absolute
   segment.end = 130.0     # Absolute
   
   # Check overlap
   if segment.end > clip_start and segment.start < clip_end:
       # Segment overlaps with clip
   ```

3. **Rebase to Relative Timestamps**
   ```python
   # Convert to clip-relative (0-based)
   relative_start = max(0, segment.start - clip_start)
   # = max(0, 120.0 - 125.5) = max(0, -5.5) = 0
   
   relative_end = min(clip_duration, segment.end - clip_start)
   # = min(14.7, 130.0 - 125.5) = min(14.7, 4.5) = 4.5
   ```

4. **Result**: Captions ready for export
   ```python
   {
       "start": 0.0,      # Relative: start of clip
       "end": 4.5,        # Relative: 4.5s into clip
       "text": "Hello world",
       "original_start": 120.0,  # Preserved for reference
       "original_end": 130.0
   }
   ```

### Implementation Location

The rebasing happens in `/projects/{media_id}/captions` endpoint:

```python
# backend/api/routes.py lines 439-457
for seg in project.transcription.segments:
    if seg.end > start and seg.start < end:  # Overlap check
        # Calculate relative timestamps
        relative_start = max(0, seg.start - start)  # Rebase
        relative_end = min(end - start, seg.end - start)  # Rebase
```

### Why This Design?

- **Export Compatibility**: Exported clips start at 0:00, so captions must be 0-based
- **Reusability**: One transcription serves multiple clips
- **Flexibility**: Clip boundaries can change without rewriting transcription data
- **Accuracy**: Handles partial overlaps (segments that start before or end after the clip)

### Example Flow

```
Source Media (10:00 duration)
├─ Transcription (absolute)
│  ├─ Segment 1: 0:00 - 0:05
│  ├─ Segment 2: 0:05 - 0:10
│  └─ Segment 3: 0:10 - 0:15
│
└─ Clip A (absolute: 0:02 - 0:12)
   └─ Rebased Captions (relative: 0:00 - 0:10)
      ├─ Partial: 0:00 - 0:03 (from Segment 1)
      ├─ Full: 0:03 - 0:08 (from Segment 2)
      └─ Partial: 0:08 - 0:10 (from Segment 3)
```

This keeps the source transcription unchanged while producing clip-specific captions for export.

---

## Design Implications

### What This Means

- **Clips are ephemeral views**: They reference media, they don't own it
- **Media is the source of truth**: All timestamps derive from the media timeline
- **Rebasing is a transformation**: Relative timestamps are computed on-demand for export
- **Storage is normalized**: One transcription, many clips, no duplication

### What This Prevents

- ❌ Storing relative timestamps in the database (would require clip_id coupling)
- ❌ Duplicating transcription data per clip
- ❌ Ambiguity about which timeline a timestamp refers to
- ❌ Cascading updates when clip boundaries change

### What This Enables

- ✅ Multiple clips from the same media share one transcription
- ✅ Easy querying: "show me all highlights between 2:00 and 3:00"
- ✅ Flexible clip boundaries without data migration
- ✅ Accurate caption generation for any clip range
