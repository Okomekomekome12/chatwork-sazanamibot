"""
yt_stream.py
YouTubeの動画・音声ストリームリンクを取得するユーティリティ

使い方:
    python yt_stream.py <YouTube URL> [オプション]

オプション:
    --quality best|worst|<height>  映像品質 (デフォルト: best)
    --audio-only                   音声ストリームのみ取得
    --list                         利用可能な全フォーマットを一覧表示
    --json                         結果をJSON形式で出力


    例:
    from yt_stream import get_stream_links, list_formats

    # ストリームリンクを取得
    info = get_stream_links("https://www.youtube.com/watch?v=XXXX", quality="720")
    print(info.url)        # 映像URL
    print(info.audio_url)  # 音声URL（映像と分離している場合）
    print(info.title)

    # フォーマット一覧を取得
    formats = list_formats("https://...")
    for f in formats:
        print(f["format_id"], f["resolution"], f["url"])
"""

import yt_dlp
import json
import argparse
import sys
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class StreamInfo:
    """取得したストリーム情報"""
    title: str
    url: str                     # 動画 or 映像ストリームURL
    audio_url: Optional[str]     # 音声ストリームURL（分離している場合）
    format_id: str
    ext: str
    resolution: Optional[str]
    fps: Optional[float]
    vcodec: Optional[str]
    acodec: Optional[str]
    filesize: Optional[int]      # バイト数（不明な場合はNone）
    is_merged: bool              # 映像と音声が同一ストリームか


def get_stream_links(
    url: str,
    quality: str = "best",
    audio_only: bool = False,
) -> StreamInfo:
    """
    YouTube動画のストリームリンクを返す。

    Parameters
    ----------
    url       : YouTube動画のURL
    quality   : 'best' / 'worst' / 高さpx文字列 (例: '720')
    audio_only: Trueにすると音声ストリームのみ取得

    Returns
    -------
    StreamInfo dataclass
    """

    # フォーマット選択文字列を組み立て
    if audio_only:
        fmt = "bestaudio/best"
    elif quality == "best":
        # 映像+音声が一体のもの優先、なければ分離ストリームを結合
        fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
    elif quality == "worst":
        fmt = "worstvideo+worstaudio/worst"
    else:
        # 指定した高さ以下で最高品質
        fmt = (
            f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]"
            f"/bestvideo[height<={quality}]+bestaudio"
            f"/best[height<={quality}]/best"
        )

    ydl_opts = {
        "format": fmt,
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,          # ダウンロードせずURLだけ取得
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    title = info.get("title", "Unknown")

    # requested_formats があれば映像と音声が分離している
    req_fmts = info.get("requested_formats")
    if req_fmts and len(req_fmts) >= 2:
        video_fmt = next((f for f in req_fmts if f.get("vcodec") != "none"), req_fmts[0])
        audio_fmt = next((f for f in req_fmts if f.get("acodec") != "none"), req_fmts[-1])
        return StreamInfo(
            title=title,
            url=video_fmt["url"],
            audio_url=audio_fmt["url"],
            format_id=video_fmt.get("format_id", ""),
            ext=video_fmt.get("ext", ""),
            resolution=video_fmt.get("resolution"),
            fps=video_fmt.get("fps"),
            vcodec=video_fmt.get("vcodec"),
            acodec=audio_fmt.get("acodec"),
            filesize=video_fmt.get("filesize") or video_fmt.get("filesize_approx"),
            is_merged=False,
        )

    # 単一ストリーム（映像+音声が一体）
    return StreamInfo(
        title=title,
        url=info["url"],
        audio_url=None,
        format_id=info.get("format_id", ""),
        ext=info.get("ext", ""),
        resolution=info.get("resolution"),
        fps=info.get("fps"),
        vcodec=info.get("vcodec"),
        acodec=info.get("acodec"),
        filesize=info.get("filesize") or info.get("filesize_approx"),
        is_merged=True,
    )


def list_formats(url: str) -> list[dict]:
    """利用可能な全フォーマットをリストで返す"""
    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = []
    for f in info.get("formats", []):
        formats.append({
            "format_id": f.get("format_id"),
            "ext":       f.get("ext"),
            "resolution": f.get("resolution", "audio only"),
            "fps":       f.get("fps"),
            "vcodec":    f.get("vcodec"),
            "acodec":    f.get("acodec"),
            "filesize":  f.get("filesize") or f.get("filesize_approx"),
            "url":       f.get("url"),
        })
    return formats


# ─── CLI ───────────────────────────────────────────────────────────────────────

def _fmt_size(n: Optional[int]) -> str:
    if not n:
        return "不明"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def main():
    parser = argparse.ArgumentParser(description="YouTube ストリームリンク取得ツール")
    parser.add_argument("url", help="YouTube動画のURL")
    parser.add_argument("--quality", default="best",
                        help="映像品質: best / worst / 高さpx (例: 720)")
    parser.add_argument("--audio-only", action="store_true",
                        help="音声ストリームのみ取得")
    parser.add_argument("--list", action="store_true",
                        help="利用可能な全フォーマットを一覧表示")
    parser.add_argument("--json", action="store_true",
                        help="JSON形式で出力")
    args = parser.parse_args()

    try:
        if args.list:
            formats = list_formats(args.url)
            if args.json:
                print(json.dumps(formats, ensure_ascii=False, indent=2))
            else:
                print(f"{'ID':<12} {'拡張子':<6} {'解像度':<14} {'FPS':<6} {'映像codec':<14} {'音声codec':<12} {'サイズ'}")
                print("-" * 80)
                for f in formats:
                    print(
                        f"{f['format_id']:<12} {f['ext']:<6} "
                        f"{str(f['resolution']):<14} {str(f['fps'] or ''):<6} "
                        f"{str(f['vcodec'] or ''):<14} {str(f['acodec'] or ''):<12} "
                        f"{_fmt_size(f['filesize'])}"
                    )
            return

        info = get_stream_links(args.url, quality=args.quality, audio_only=args.audio_only)

        if args.json:
            print(json.dumps(asdict(info), ensure_ascii=False, indent=2))
        else:
            print(f"\n🎬 タイトル  : {info.title}")
            print(f"   フォーマット: {info.format_id} ({info.ext})")
            print(f"   解像度    : {info.resolution or 'N/A'}  FPS: {info.fps or 'N/A'}")
            print(f"   映像codec : {info.vcodec or 'N/A'}")
            print(f"   音声codec : {info.acodec or 'N/A'}")
            print(f"   サイズ    : {_fmt_size(info.filesize)}")
            print(f"\n📺 映像URL:\n  {info.url}")
            if info.audio_url:
                print(f"\n🎵 音声URL（分離）:\n  {info.audio_url}")
            print()

    except yt_dlp.utils.DownloadError as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()