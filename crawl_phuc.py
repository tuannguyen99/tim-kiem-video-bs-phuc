#!/usr/bin/env python3
"""
Lấy phụ đề toàn bộ video kênh "Bác sĩ Trần Văn Phúc Official" và xuất ra
một file JSON gọn để nạp vào trang tra cứu.

Cài đặt (một lần):
    pip install -U yt-dlp youtube-transcript-api

Chạy:
    python crawl_phuc.py                  # lấy tất cả, ghi ra data.json
    python crawl_phuc.py --limit 5        # thử với 5 video trước
    python crawl_phuc.py --retry-failed   # thử lại các video lần trước bị lỗi

Script chạy tiếp được: video đã lấy rồi sẽ được bỏ qua, nên lần sau chạy lại
chỉ lấy video mới. Nên chạy từ mạng nhà (IP dân dụng); IP máy chủ/cloud hay bị
YouTube chặn.
"""
import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone

try:
    import yt_dlp
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    sys.exit("Thiếu thư viện. Chạy: pip install -U yt-dlp youtube-transcript-api")

CHANNEL_ID = "UC79E6KatRfXbmdWVWGncsew"
CHANNEL_NAME = "Bác sĩ Trần Văn Phúc Official"
TABS = ["videos", "streams"]  # video thường + video livestream
LANGS = ["vi"]

# Lỗi cho thấy YouTube đang chặn IP -> dừng ngay, lưu lại, chạy sau.
BLOCKED_ERRORS = {"RequestBlocked", "IpBlocked", "TooManyRequests", "YouTubeRequestFailed"}


def log(msg):
    print(msg, flush=True)


def list_channel_videos():
    """Trả về danh sách [{id, title, duration, upload_date}] theo thứ tự mới -> cũ."""
    opts = {"extract_flat": True, "quiet": True, "skip_download": True, "ignoreerrors": True}
    seen, videos = set(), []
    with yt_dlp.YoutubeDL(opts) as ydl:
        for tab in TABS:
            url = f"https://www.youtube.com/channel/{CHANNEL_ID}/{tab}"
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:  # tab có thể không tồn tại
                log(f"  (bỏ qua tab {tab}: {e})")
                continue
            for e in (info or {}).get("entries") or []:
                if not e or not e.get("id") or e["id"] in seen:
                    continue
                seen.add(e["id"])
                videos.append({
                    "id": e["id"],
                    "title": e.get("title") or "",
                    "duration": e.get("duration"),
                    "upload_date": e.get("upload_date"),  # thường None ở chế độ flat
                })
    return videos


def fetch_transcript(api, vid):
    """Trả về (kind, segments) với segments = [[start_giây, text], ...]."""
    tlist = api.list(vid)
    transcript, kind = None, None
    try:
        transcript, kind = tlist.find_manually_created_transcript(LANGS), "manual"
    except Exception:
        try:
            transcript, kind = tlist.find_generated_transcript(LANGS), "auto"
        except Exception:
            # Không có tiếng Việt: lấy bất kỳ ngôn ngữ nào có sẵn
            for t in tlist:
                transcript, kind = t, ("auto" if t.is_generated else "manual") + ":" + t.language_code
                break
    if transcript is None:
        raise RuntimeError("NoTranscript")
    segs = []
    for s in transcript.fetch():
        text = " ".join((s.text or "").split())
        if text and text not in ("[Âm nhạc]", "[Music]"):
            segs.append([round(float(s.start), 1), text])
    return kind, segs


def load(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"v": 1, "channel": {"id": CHANNEL_ID, "name": CHANNEL_NAME}, "videos": [], "skipped": {}}


def save(path, data):
    data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description="Lấy phụ đề kênh Bác sĩ Trần Văn Phúc")
    ap.add_argument("-o", "--out", default="data.json", help="file JSON đầu ra (mặc định data.json)")
    ap.add_argument("--limit", type=int, default=0, help="chỉ lấy N video mới (để thử)")
    ap.add_argument("--retry-failed", action="store_true", help="thử lại các video lần trước bị lỗi")
    ap.add_argument("--delay", type=float, default=2.0, help="giây nghỉ trung bình giữa các video")
    args = ap.parse_args()

    data = load(args.out)
    done = {v["id"] for v in data["videos"]}
    skipped = data.setdefault("skipped", {})

    log("Đang lấy danh sách video của kênh...")
    videos = list_channel_videos()
    log(f"Kênh có {len(videos)} video. Đã có phụ đề: {len(done)}.")

    # Cập nhật thứ tự và tiêu đề cho video đã có (tiêu đề có thể bị đổi)
    order = {v["id"]: i for i, v in enumerate(videos)}
    meta = {v["id"]: v for v in videos}
    for v in data["videos"]:
        if v["id"] in meta:
            v["o"] = order[v["id"]]
            v["t"] = meta[v["id"]]["title"] or v["t"]

    todo = [v for v in videos if v["id"] not in done and (args.retry_failed or v["id"] not in skipped)]
    if args.limit:
        todo = todo[: args.limit]
    log(f"Cần lấy: {len(todo)} video.\n")

    api = YouTubeTranscriptApi()
    ok = fail = 0
    for n, v in enumerate(todo, 1):
        vid = v["id"]
        try:
            kind, segs = fetch_transcript(api, vid)
        except Exception as e:
            name = type(e).__name__
            if name in BLOCKED_ERRORS:
                save(args.out, data)
                log(f"\nYouTube đang chặn ({name}). Đã lưu {ok} video mới. Chờ vài giờ rồi chạy lại.")
                sys.exit(2)
            reason = name if name != "RuntimeError" else str(e)
            skipped[vid] = reason
            fail += 1
            log(f"[{n}/{len(todo)}] ✗ {vid} {v['title'][:60]} — {reason}")
        else:
            skipped.pop(vid, None)
            item = {"id": vid, "t": v["title"], "o": order.get(vid, 9999), "k": kind, "s": segs}
            if v.get("duration"):
                item["dur"] = int(v["duration"])
            if v.get("upload_date"):
                item["d"] = v["upload_date"]
            data["videos"].append(item)
            ok += 1
            log(f"[{n}/{len(todo)}] ✓ {vid} {v['title'][:60]} — {len(segs)} dòng ({kind})")
        save(args.out, data)
        if n < len(todo):
            time.sleep(args.delay * random.uniform(0.6, 1.6))

    data["videos"].sort(key=lambda x: x.get("o", 9999))
    save(args.out, data)
    size_mb = os.path.getsize(args.out) / 1_048_576
    log(f"\nXong: +{ok} video, lỗi {fail}. Tổng {len(data['videos'])} video có phụ đề.")
    log(f"File: {os.path.abspath(args.out)} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
