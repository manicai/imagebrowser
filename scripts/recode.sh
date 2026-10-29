#!/bin/bash
# Convert videos to browser-playable MP4 (H.264/AAC, at most 1080p).
#
#   recode.sh [-n] FILE...
#
#   -n  dry run: print what would happen to each file and change nothing.
#
# Each FILE becomes NAME.mp4 next to it:
#   - already H.264/AAC and at most 1080p: remuxed with ffmpeg (lossless, fast)
#   - H.264 video but other audio: video copied, audio converted to AAC
#   - otherwise: re-encoded with x264, deinterlacing if needed and
#     downscaling anything above 1080p
#   - already a compatible NAME.mp4: left alone
# The original is removed only after a successful conversion. The
# modification time is carried over.
set -euo pipefail

# Cap the long edge at 1920 so 4K becomes 1080p in landscape or portrait.
MAX_EDGE=1920
CRF=20
# Deinterlace only frames flagged as interlaced. Scale the long edge down to
# MAX_EDGE (never up) and keep both dimensions even, as yuv420p requires.
VIDEO_FILTER="bwdif=deint=interlaced,\
scale='if(gte(iw,ih),trunc(min($MAX_EDGE,iw)/2)*2,-2)':\
'if(gte(iw,ih),-2,trunc(min($MAX_EDGE,ih)/2)*2)'"

dry_run=false
tmp=""
cleanup() { if [[ -n "$tmp" ]]; then rm -f "$tmp"; fi; }
trap cleanup EXIT

# Print "skip", "remux", "audio" or "encode" for $1, with the reason on stderr.
plan() {
    local input=$1 output=$2
    local codec_name="" width=0 height=0 pix_fmt="" k v

    while IFS='=' read -r k v; do
        case $k in
            codec_name|width|height|pix_fmt) printf -v "$k" '%s' "$v" ;;
        esac
    done < <(ffprobe -v error -select_streams v:0 \
                 -show_entries stream=codec_name,width,height,pix_fmt \
                 -of default=noprint_wrappers=1 "$input")

    if [[ -z "$codec_name" ]]; then
        echo "no video stream found" >&2
        return 1
    fi

    local audio
    audio=$(ffprobe -v error -select_streams a \
                -show_entries stream=codec_name -of csv=p=0 "$input" \
            | grep -vx aac || true)

    local why=""
    [[ "$codec_name" != h264 ]] && why+=" video=$codec_name"
    [[ "$pix_fmt" != yuv420p && "$pix_fmt" != yuvj420p ]] && why+=" pix_fmt=$pix_fmt"
    (( width > MAX_EDGE || height > MAX_EDGE )) && why+=" size=${width}x${height}"
    audio=$(echo $audio | tr ' ' ',')

    if [[ -n "$why" ]]; then
        echo "needs encode:$why${audio:+ audio=$audio}" >&2
        echo encode
    elif [[ -n "$audio" ]]; then
        echo "needs audio conversion: audio=$audio" >&2
        echo audio
    elif [[ "$input" == "$output" ]]; then
        echo "already compatible" >&2
        echo skip
    else
        echo "compatible ${width}x${height}" >&2
        echo remux
    fi
}

recode() {
    local input=$1
    local output="${input%.*}.mp4"
    local action

    if [[ ! -f "$input" ]]; then
        echo "recode: $input: no such file" >&2
        return 1
    fi
    if [[ -e "$output" && ! "$output" -ef "$input" ]]; then
        echo "recode: $output already exists, skipping $input" >&2
        return 1
    fi

    echo -n "recode: $input: " >&2
    action=$(plan "$input" "$output") || return 1
    if [[ "$action" == skip ]] || $dry_run; then
        [[ "$action" != skip ]] && echo "recode: would $action $input -> $output"
        return 0
    fi

    # Temp file next to the output so the final mv is an atomic rename.
    tmp=$(mktemp -p "$(dirname "$output")" --suffix=.mp4 .recode.XXXXXX)

    # set -e does not apply inside a function called with ||, so check each
    # step explicitly.
    local ok=true
    if [[ "$action" == remux ]]; then
        ffmpeg -v error -y -i "$input" -map 0:v:0 -map '0:a?' -c copy \
            -movflags +faststart "$tmp" || ok=false
    elif [[ "$action" == audio ]]; then
        ffmpeg -v error -y -i "$input" -map 0:v:0 -map '0:a?' -c:v copy \
            -c:a aac -b:a 192k -movflags +faststart "$tmp" || ok=false
    else
        ffmpeg -v error -y -i "$input" -map 0:v:0 -map '0:a?' \
            -vf "$VIDEO_FILTER" -c:v libx264 -preset slow -crf "$CRF" \
            -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart \
            "$tmp" || ok=false
    fi
    if ! $ok || [[ ! -s "$tmp" ]]; then
        echo "recode: ${action} of $input failed, original kept" >&2
        rm -f "$tmp"
        tmp=""
        return 1
    fi

    touch -r "$input" "$tmp" || return 1
    chmod 644 "$tmp" || return 1
    mv "$tmp" "$output" || return 1
    tmp=""
    if [[ ! "$input" -ef "$output" ]]; then
        rm "$input"
    fi
    echo "recode: $input -> $output ($action)"
}

if [[ "${1:-}" == -n ]]; then
    dry_run=true
    shift
fi
if [[ $# -eq 0 ]]; then
    echo "usage: $0 [-n] FILE..." >&2
    exit 2
fi

status=0
for f in "$@"; do
    recode "$f" || status=1
done
exit $status
