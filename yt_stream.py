"""
yt_stream.py
YouTubeの動画・音声ストリームリンクを取得するユーティリティ

使い方:
    python yt_stream.py <YouTube URL> [オプション]

オプション:
    --quality best|worst|<height>  映像品質 (デフォルト: best)
    --audio-only                   音声ストリームのみ取得
    --hls                          HLS (m3u8) ストリームURLを取得
    --list                         利用可能な全フォーマットを一覧表示
    --json                         結果をJSON形式で出力
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
    protocol: Optional[str]      # https / m3u8_native / m3u8 など
    resolution: Optional[str]
    fps: Optional[float]
    vcodec: Optional[str]
    acodec: Optional[str]
    filesize: Optional[int]
    is_merged: bool


def _build_stream_info(info: dict, audio_url: Optional[str] = None, is_merged: bool = True) -> StreamInfo:
    return StreamInfo(
        title=info.get("title", "Unknown"),
        url=info["url"],
        audio_url=audio_url,
        format_id=info.get("format_id", ""),
        ext=info.get("ext", ""),
        protocol=info.get("protocol"),
        resolution=info.get("resolution"),
        fps=info.get("fps"),
        vcodec=info.get("vcodec"),
        acodec=info.get("acodec"),
        filesize=info.get("filesize") or info.get("filesize_approx"),
        is_merged=is_merged,
    )


def get_stream_links(
    url: str,
    quality: str = "best",
    audio_only: bool = False,
) -> StreamInfo:
    """
    YouTube動画の統合ストリーム（映像+音声が1URL）を返す。
    ※ YouTubeは480p以下にのみ統合ストリームを提供している場合が多い。
    """
    if audio_only:
        fmt = "bestaudio/best"
    elif quality == "best":
        fmt = "best[vcodec!=none][acodec!=none]"
    elif quality == "worst":
        fmt = "worst[vcodec!=none][acodec!=none]"
    else:
        fmt = f"best[vcodec!=none][acodec!=none][height<={quality}]"

    ydl_opts = {
        "format": fmt,
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info.get("url"):
        raise ValueError(
            "統合ストリームが見つかりませんでした。\n"
            "--list で利用可能なフォーマットを確認してください。"
        )

    return _build_stream_info(info)


def get_hls_url(url: str, quality: str = "best") -> StreamInfo:
    """
    HLS (m3u8) ストリームのURLを取得する。
    manifest.googlevideo.com 形式のURLが返る。

    注意:
      - YouTubeの多くの通常動画にはHLSが存在しない（ライブ配信には存在する）。
        存在しない場合は ValueError を送出する。
      - 有効期限が短いため、取得後すぐに使用すること。
      - ffmpeg で保存する場合: ffmpeg -i "<m3u8_url>" -c copy output.mp4
    """
    # まず全フォーマットを取得してHLSの有無を確認
    ydl_opts_check = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}
    with yt_dlp.YoutubeDL(ydl_opts_check) as ydl:
        info_all = ydl.extract_info(url, download=False)

    hls_formats = [
        f for f in info_all.get("formats", [])
        if f.get("protocol") in ("m3u8_native", "m3u8")
    ]

    if not hls_formats:
        available = sorted({f.get("protocol", "unknown") for f in info_all.get("formats", [])})
        raise ValueError(
            f"この動画にはHLS (m3u8) フォーマットが存在しません。\n"
            f"利用可能なプロトコル: {available}\n"
            f"ヒント: HLSはライブ配信やプレミア公開中の動画に存在することが多いです。\n"
            f"通常の動画には get_stream_links() を使用してください。"
        )

    # HLS が存在する場合のみ品質フィルタで再取得
    if quality == "best":
        fmt = (
            "best[protocol=m3u8_native][vcodec!=none][acodec!=none]"
            "/best[protocol=m3u8][vcodec!=none][acodec!=none]"
            "/best[protocol=m3u8_native]"
            "/best[protocol=m3u8]"
        )
    elif quality == "worst":
        fmt = (
            "worst[protocol=m3u8_native][vcodec!=none][acodec!=none]"
            "/worst[protocol=m3u8][vcodec!=none][acodec!=none]"
            "/worst[protocol=m3u8_native]"
            "/worst[protocol=m3u8]"
        )
    else:
        fmt = (
            f"best[protocol=m3u8_native][height<={quality}][vcodec!=none][acodec!=none]"
            f"/best[protocol=m3u8][height<={quality}][vcodec!=none][acodec!=none]"
            f"/best[protocol=m3u8_native][height<={quality}]"
            f"/best[protocol=m3u8][height<={quality}]"
        )

    ydl_opts = {
        "format": fmt,
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info.get("url"):
        raise ValueError("HLS URLの取得に失敗しました。")

    return _build_stream_info(info)


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
            "protocol":  f.get("protocol"),
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
    parser.add_argument("--hls", action="store_true",
                        help="HLS (m3u8) ストリームURLを取得 (主にライブ配信向け)")
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
                print(f"{'ID':<12} {'拡張子':<6} {'プロトコル':<20} {'解像度':<14} {'FPS':<6} {'映像codec':<14} {'音声codec':<12} {'サイズ'}")
                print("-" * 105)
                for f in formats:
                    print(
                        f"{f['format_id']:<12} {f['ext']:<6} "
                        f"{str(f['protocol'] or ''):<20} "
                        f"{str(f['resolution']):<14} {str(f['fps'] or ''):<6} "
                        f"{str(f['vcodec'] or ''):<14} {str(f['acodec'] or ''):<12} "
                        f"{_fmt_size(f['filesize'])}"
                    )
            return

        if args.hls:
            info = get_hls_url(args.url, quality=args.quality)
        else:
            info = get_stream_links(args.url, quality=args.quality, audio_only=args.audio_only)

        if args.json:
            print(json.dumps(asdict(info), ensure_ascii=False, indent=2))
        else:
            print(f"\n🎬 タイトル  : {info.title}")
            print(f"   フォーマット: {info.format_id} ({info.ext})")
            print(f"   プロトコル  : {info.protocol or 'N/A'}")
            print(f"   解像度    : {info.resolution or 'N/A'}  FPS: {info.fps or 'N/A'}")
            print(f"   映像codec : {info.vcodec or 'N/A'}")
            print(f"   音声codec : {info.acodec or 'N/A'}")
            print(f"   サイズ    : {_fmt_size(info.filesize)}")
            print(f"\n📺 URL:\n  {info.url}")
            if info.audio_url:
                print(f"\n🎵 音声URL（分離）:\n  {info.audio_url}")
            print()

    except (yt_dlp.utils.DownloadError, ValueError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()