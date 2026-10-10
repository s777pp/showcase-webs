"""Background job of the AI animation tab (worker ``gpu`` queue, or the embedded pool without a worker).

Stages (shown in the tab): prepare -> wish -> sending -> animating (time based, the model takes 1-3 min) ->
assembling (background, loop) -> encoding (MP4 + GIF) -> done. A refused, failed or cancelled job gives its daily
use back (smweb.ai_animate.give_back)."""
from __future__ import annotations

import shutil
import time
import traceback
from pathlib import Path

import redis_store as rs
from smweb import ai_animate, job_diagnostics, process_control, saved_results

REFUSED_TEXT = ("The AI service refused this picture under its content rules. Your try was not spent. "
                "Pictures with nudity cannot be animated.")


def run(jid: str, job: dict) -> None:
    root = Path(str(job["job_dir"]))
    source = Path(str(job["source_path"]))
    ticket = job.get("ticket")
    if process_control.cancelled(jid):
        # Cancelled while queued: the cancel route already gave the use back.
        process_control.mark_cancelled(jid)
        shutil.rmtree(root, ignore_errors=True)
        return
    try:
        with process_control.job_context(jid):
            rs.job_update(jid, status="running", pct=4, stage="prepare")
            wish_en = ""
            if job.get("wish"):
                rs.job_update(jid, pct=6, stage="wish")
                wish_en = ai_animate.rewrite_wish(str(job["wish"]))
            prompt = ai_animate.build_prompt(str(job.get("mode") or "calm"), list(job.get("motions") or []), wish_en)
            rs.job_update(jid, pct=9, stage="sending", prompt=prompt)
            clip = root / "clip.mp4"

            def progress(status: str, elapsed: float) -> None:
                pct = 10 + round(60 * min(1.0, elapsed / 150))
                rs.job_update(jid, pct=pct, stage="queued_ai" if status == "IN_QUEUE" else "animating")

            info = ai_animate.generate(source, prompt, clip, jid=jid, progress=progress)
            process_control.checkpoint(jid)
            rs.job_update(jid, pct=74, stage="assembling", ai_seconds=info.get("seconds"))
            stem = str(job.get("stem") or "animation")
            result = ai_animate.render(clip, source, root, seconds=int(job.get("seconds") or 3),
                                       keep_background=bool(job.get("keep_background", True)), jid=jid, stem=stem)
            clip.unlink(missing_ok=True)
            rs.job_update(jid, pct=96, stage="saving")
            saved_id = None
            try:
                saved_id = saved_results.save_job_result(jid, user_key=str(job.get("user_key") or ""),
                                                         result_path=Path(result["gif"]), kind="ai_animate",
                                                         mode=str(job.get("mode") or ""), title=stem[:80], file_count=1)
            except Exception:
                pass
            rs.job_update(jid, status="done", pct=100, stage="done", finished=time.time(),
                          gif_path=result["gif"], mp4_path=result["mp4"], gif_bytes=result["gif_bytes"],
                          mp4_bytes=result["mp4_bytes"], out_width=result["gif_width"], out_height=result["gif_height"],
                          out_fps=result["fps"], out_frames=result["frames"], moving_pct=result["moving_pct"],
                          crossfade=result["crossfade"], saved_id=saved_id or "")
    except process_control.JobCancelled:
        ai_animate.give_back(ticket)
        process_control.mark_cancelled(jid)
        shutil.rmtree(root, ignore_errors=True)
    except ai_animate.Refused as exc:
        ai_animate.give_back(ticket)
        rs.job_update(jid, status="error", pct=100, stage="error", error=REFUSED_TEXT, error_code="ai_moderated",
                      finished=time.time(), error_traces=[job_diagnostics.trace_text(exc, root)])
    except Exception as exc:
        traceback.print_exc()
        ai_animate.give_back(ticket)
        user_error = str(exc)[:200] if isinstance(exc, ValueError) else "AI animation failed"
        rs.job_update(jid, status="error", pct=100, stage="error", error=user_error, finished=time.time(),
                      error_detail=job_diagnostics.scrub(f"{type(exc).__name__}: {exc}", root)[:500],
                      error_traces=[job_diagnostics.trace_text(exc, root)])
