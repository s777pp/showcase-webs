"""Manual private test. Default is a local dry run; --confirm-cost opts into GPU use."""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class SafeTestError(RuntimeError):
    """Only locally authored, credential-free messages may be displayed."""


def save_result(storage, request_id, output):
    from smweb.animation_experiment import MAX_OUTPUT_BYTES, keys
    _, result_key = keys(request_id)
    response = storage.client().get_object(Bucket=storage.PRIVATE_BUCKET, Key=result_key)
    stream = response["Body"]
    try:
        if not 0 < response.get("ContentLength", 0) <= MAX_OUTPUT_BYTES:
            raise ValueError("Invalid output size")
        # Allocate exclusively: neither the chosen output nor an existing file is overwritten.
        output.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        with output.open("xb") as destination:
            try:
                while chunk := stream.read(65536):
                    if written == 0 and (len(chunk) < 12 or chunk[4:8] != b"ftyp"):
                        raise ValueError("Result is not MP4")
                    written += len(chunk)
                    if written > MAX_OUTPUT_BYTES:
                        raise ValueError("Output too large")
                    destination.write(chunk)
                if written != response["ContentLength"]:
                    raise ValueError("Incomplete result download")
            except BaseException:
                destination.close()
                output.unlink()  # Only the new file exclusively created above.
                raise
    finally:
        stream.close()


def main(argv=None):
    from dotenv import load_dotenv
    from smweb.animation_experiment import (
        INTENSITIES, MAX_INPUT_BYTES, PRESETS, PROFILES, PROTOCOL_VERSION, Submission, keys, prepare_image,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=Path)
    group.add_argument("--health", action="store_true")
    group.add_argument("--resume", metavar="REQUEST_ID")
    group.add_argument("--cancel", metavar="REQUEST_ID", help="Cancel this experiment request, including its running GPU container")
    parser.add_argument("--preset", choices=(*PRESETS, "custom"), default="alive")
    parser.add_argument("--intensity", choices=tuple(INTENSITIES), default="normal")
    parser.add_argument("--quality", choices=tuple(PROFILES), default="draft")
    parser.add_argument("--prompt", default="", help="English motion description for --preset custom")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--matte", default="#061019")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--confirm-cost", action="store_true", help="Allow private R2 upload and paid Modal GPU generation")
    args = parser.parse_args(argv)
    load_dotenv(args.env_file, override=False)

    if args.health:
        from smweb.modal_animation_client import AnimationClient
        print(json.dumps(AnimationClient().health(), ensure_ascii=False))
        return 0
    if args.cancel:
        keys(args.cancel)
        from smweb.modal_animation_client import AnimationClient
        print(json.dumps(AnimationClient().cancel(args.cancel)))
        return 0
    if args.resume:
        request_id = args.resume
        keys(request_id)
    else:
        if not args.image.is_file() or args.image.stat().st_size > MAX_INPUT_BYTES:
            raise SafeTestError("Choose an existing image, maximum 8 MB")
        request_id = uuid.uuid4().hex
    output = (args.output or ROOT / "animation-test-results" / f"{request_id}.mp4").resolve()
    if output.suffix.lower() != ".mp4" or output.exists():
        raise SafeTestError("Choose a new, nonexisting .mp4 output file")
    if not args.resume:
        if (args.preset == "custom") != bool(args.prompt.strip()) or len(args.prompt) > 1000:
            raise SafeTestError("Use a prompt of 1–1000 characters only with --preset custom")
        if not 0 <= args.seed <= 2147483647:
            raise SafeTestError("Seed must be between 0 and 2147483647")
        try:
            image = prepare_image(args.image.read_bytes(), args.matte)
        except ValueError:
            raise SafeTestError("Use a static PNG/JPEG/WebP, minimum side 64 px, maximum 16 megapixels and aspect ratio between 1:3 and 3:1; matte must be #RRGGBB") from None
        prepared = io.BytesIO()
        image.save(prepared, format="PNG")
        print(f"Canvas: {image.width}x{image.height}; preset: {args.preset}; intensity: {args.intensity}; quality: {args.quality}")
        frames, steps = PROFILES[args.quality]
        print(f"Generation: {frames} frames, {steps} steps. Quality mode costs more GPU time than draft.")
        print("Transparency is composited over the matte; output is MP4, not a guaranteed seamless loop.")
        if not args.confirm_cost:
            print("Dry run complete. No upload or GPU call. Add --confirm-cost to generate.")
            return 0

    # Environment-sensitive imports happen AFTER loading the chosen .env.
    from smweb import object_store as storage
    from smweb.modal_animation_client import AnimationClient
    client = AnimationClient()
    if not storage.configured():
        raise SafeTestError("Configure private R2 storage in .env, as for Modal upscale")
    source_key, result_key = keys(request_id)
    print(f"Request id: {request_id}", flush=True)
    print(f"To resume without another GPU submission: --resume {request_id}", flush=True)
    if not args.resume:
        payload = Submission(
            request_id=request_id,
            source_url=storage.presigned_get_url(source_key, expires=7200),
            result_url=storage.presigned_put_url(result_key, expires=7200),
            preset=args.preset, intensity=args.intensity, quality=args.quality, prompt=args.prompt,
            seed=args.seed, matte=args.matte,
        )
        health = client.health()  # Fail before upload, not after paying for an old preset.
        if health.get("protocol_version") != PROTOCOL_VERSION:
            raise SafeTestError(f"Redeploy the updated modal_animate.py before generating: service protocol must be {PROTOCOL_VERSION}. No image was uploaded.")
        storage.put_bytes(source_key, prepared.getvalue(), public=False, media_type="image/png")
        client.submit(payload.model_dump())  # Intentionally no retry on ambiguous transport errors.

    deadline = time.monotonic() + 7200
    last_progress = None
    last_report = 0
    while time.monotonic() < deadline:
        ready, result = client.result(request_id)
        if ready:
            if result.get("status") != "done":
                explanations = {
                    "gpu_memory": "GPU ran out of memory.",
                    "execution_not_repeated": "An earlier execution was interrupted; expensive replay was blocked.",
                    "cancelled": "The request was cancelled.",
                }
                detail = explanations.get(result.get("code"), "GPU task failed.")
                raise SafeTestError(detail + " Inspect Modal logs; no automatic retry. Input remains private in R2.")
            save_result(storage, request_id, output)
            print(f"Saved: {output}")
            print(f"Video: {result.get('width')}x{result.get('height')}, {result.get('frames')} frames, {result.get('fps')} fps")
            motion = result.get("motion", {})
            if motion.get("status") == "low_motion":
                print("WARNING: weak foreground motion detected. MP4 saved for inspection; no paid retry was started.")
            elif motion.get("status") == "motion_detected":
                print("Temporal changes detected. This is a pixel-based check, not a guarantee of useful character motion.")
            else:
                print("Motion check unavailable or inconclusive; inspect the MP4 manually.")
            # Only allowlisted metadata; never persist signed URLs or service bodies.
            metadata = {key: result[key] for key in ("width", "height", "frames", "fps", "bytes", "seed", "preset", "intensity", "quality", "motion") if key in result}
            try:
                with output.with_suffix(".json").open("x", encoding="utf-8") as sidecar:
                    json.dump({"request_id": request_id, **metadata}, sidecar, indent=2)
            except OSError:
                print("Metadata sidecar was not written; existing files were preserved.")
            # Delete only this test's two remote objects, after the download succeeded.
            try:
                storage.delete(source_key, public=False)
                storage.delete(result_key, public=False)
                print("Removed this test's private R2 input and result; local MP4 is retained.")
            except Exception:
                print("Saved locally, but R2 cleanup failed. Remove this request's two objects manually.")
            return 0
        if result.get("status") == "unknown":
            raise SafeTestError("Submission outcome unknown. Inspect the animation app dashboard; do not submit a new request automatically.")
        state = (result.get("stage", result.get("status", "queued")), result.get("step"), result.get("total"))
        if state != last_progress or time.monotonic() - last_report >= 60:
            print(f"Waiting: {state[0]}" + (f"; step {state[1]}/{state[2]}" if state[1] is not None else ""), flush=True)
            last_progress, last_report = state, time.monotonic()
        time.sleep(10)
    raise SafeTestError("Wait timed out. Use --resume with the same request id, not a new submission. Cancel with --cancel REQUEST_ID to stop the GPU task.")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Stopped waiting; the remote task may still run. Resume using the printed request id.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as error:
        # SDK/HTTP exceptions can include presigned URLs; never print them or a traceback.
        from smweb.modal_animation_client import AnimationServiceError
        safe = type(error) in (AnimationServiceError, SafeTestError)
        print(str(error) if safe else f"Test failed ({type(error).__name__}); check configuration privately.", file=sys.stderr)
        raise SystemExit(1)
