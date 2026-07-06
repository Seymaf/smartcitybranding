#!/usr/bin/env bash
#
# Haftalık podcast ses klonlama sistemi - kurulum betiği
# Bu betik KENDİ bilgisayarınızda (Mac/Linux) çalıştırılmak içindir.
#
# Kullanım:  bash setup.sh
#
set -euo pipefail

WORKDIR="$HOME/smartcity-podcast"
VENV_DIR="$WORKDIR/.venv"
SCRIPT_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

say()  { printf '\n\033[1;36m==>\033[0m %s\n' "$1"; }
warn() { printf '\n\033[1;33m[UYARI]\033[0m %s\n' "$1"; }
err()  { printf '\n\033[1;31m[HATA]\033[0m %s\n' "$1"; }

say "1/6 - Donanim tespiti yapiliyor..."

OS_NAME="$(uname -s)"
ARCH_NAME="$(uname -m)"
HW_MODE="cpu"

if [[ "$OS_NAME" == "Darwin" && "$ARCH_NAME" == "arm64" ]]; then
    HW_MODE="mps"
    echo "Apple Silicon Mac tespit edildi (uman $ARCH_NAME). PyTorch, MPS (Metal) hizlandirmasiyla kurulacak."
elif command -v nvidia-smi >/dev/null 2>&1; then
    HW_MODE="cuda"
    echo "NVIDIA GPU tespit edildi. PyTorch, CUDA destegiyle kurulacak."
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || true
else
    HW_MODE="cpu"
    warn "GPU/Apple Silicon bulunamadi, sadece CPU ile devam edilecek."
    warn "Bu durumda uretim YAVAS olur: ~4 dakikalik bir podcast icin 10-20 dakika surebilir."
fi

RAM_GB="bilinmiyor"
if [[ "$OS_NAME" == "Darwin" ]]; then
    RAM_BYTES="$(sysctl -n hw.memsize 2>/dev/null || echo 0)"
    RAM_GB=$(( RAM_BYTES / 1024 / 1024 / 1024 ))
elif [[ -r /proc/meminfo ]]; then
    RAM_KB="$(awk '/MemTotal/ {print $2}' /proc/meminfo)"
    RAM_GB=$(( RAM_KB / 1024 / 1024 ))
fi
echo "Isletim sistemi : $OS_NAME ($ARCH_NAME)"
echo "RAM              : ${RAM_GB} GB"
echo "Secilen mod      : $HW_MODE"

if [[ "$RAM_GB" != "bilinmiyor" && "$RAM_GB" -lt 8 ]]; then
    warn "8GB'dan az RAM tespit edildi. Model yuklemesi sirasinda yavaslama veya bellek hatasi olabilir."
fi

say "2/6 - Python 3.10+ kontrol ediliyor..."

find_python() {
    for cand in python3.12 python3.11 python3.10 python3; do
        if command -v "$cand" >/dev/null 2>&1; then
            ver="$("$cand" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
            major="${ver%.*}"; minor="${ver#*.}"
            if [[ "$major" -eq 3 && "$minor" -ge 10 ]]; then
                echo "$cand"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON_BIN="$(find_python || true)"
if [[ -z "${PYTHON_BIN:-}" ]]; then
    warn "Python 3.10+ bulunamadi, kurulmaya calisilacak."
    if [[ "$OS_NAME" == "Darwin" ]]; then
        if ! command -v brew >/dev/null 2>&1; then
            err "Homebrew bulunamadi. Lutfen once https://brew.sh adresinden Homebrew'u kurun, sonra bu betigi tekrar calistirin."
            exit 1
        fi
        brew install python@3.11
        PYTHON_BIN="python3.11"
    elif command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update -y
        sudo apt-get install -y python3.11 python3.11-venv python3-pip
        PYTHON_BIN="python3.11"
    else
        err "Otomatik Python kurulumu bu sistemde desteklenmiyor. Lutfen Python 3.10+ kurup betigi tekrar calistirin."
        exit 1
    fi
fi
echo "Kullanilacak Python: $PYTHON_BIN ($("$PYTHON_BIN" --version))"

say "3/6 - ffmpeg kontrol ediliyor..."

if ! command -v ffmpeg >/dev/null 2>&1; then
    warn "ffmpeg bulunamadi, kuruluyor..."
    if [[ "$OS_NAME" == "Darwin" ]]; then
        command -v brew >/dev/null 2>&1 && brew install ffmpeg || { err "Homebrew yok, ffmpeg kurulamadi. https://brew.sh"; exit 1; }
    elif command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update -y
        sudo apt-get install -y ffmpeg
    else
        err "ffmpeg otomatik kurulamadi. Lutfen elle kurun: https://ffmpeg.org/download.html"
        exit 1
    fi
else
    echo "ffmpeg zaten kurulu: $(ffmpeg -version | head -1)"
fi

say "4/6 - Proje klasoru olusturuluyor: $WORKDIR"

mkdir -p "$WORKDIR/ses_ornegim" "$WORKDIR/scriptler" "$WORKDIR/cikti"
cp -n "$SCRIPT_SOURCE_DIR/podcast_uret.py" "$WORKDIR/podcast_uret.py" 2>/dev/null || cp -f "$SCRIPT_SOURCE_DIR/podcast_uret.py" "$WORKDIR/podcast_uret.py"
if [[ -f "$SCRIPT_SOURCE_DIR/scriptler/ornek_bu_hafta.txt" && ! -f "$WORKDIR/scriptler/ornek_bu_hafta.txt" ]]; then
    cp "$SCRIPT_SOURCE_DIR/scriptler/ornek_bu_hafta.txt" "$WORKDIR/scriptler/ornek_bu_hafta.txt"
fi
echo "Klasor yapisi hazir:"
echo "  $WORKDIR/ses_ornegim/   -> referans ses kaydinizi buraya koyun (wav/mp3/m4a)"
echo "  $WORKDIR/scriptler/     -> haftalik podcast metinleriniz (.txt)"
echo "  $WORKDIR/cikti/         -> uretilen MP3'ler burada olusacak"

say "5/6 - Python sanal ortami ve kutuphaneler kuruluyor (bu birkac dakika surebilir)..."

"$PYTHON_BIN" -m venv "$VENV_DIR"
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
pip install --upgrade pip setuptools wheel >/dev/null

case "$HW_MODE" in
    cuda)
        pip install torch --index-url https://download.pytorch.org/whl/cu121
        ;;
    mps)
        pip install torch
        ;;
    cpu)
        pip install torch --index-url https://download.pytorch.org/whl/cpu
        ;;
esac

echo "TTS (Coqui XTTS-v2) kutuphanesi kuruluyor..."
if ! pip install TTS; then
    warn "Orijinal 'TTS' paketi kurulamadi, topluluk tarafindan surdurulen 'coqui-tts' fork'u deneniyor..."
    pip install coqui-tts
fi

pip install pydub

say "6/6 - Kurulum testi calistiriliyor..."
cd "$WORKDIR"
cat > /tmp/podcast_test_script.txt <<'EOF'
=====
BASLIK: Kurulum Testi
=====
Hello, this is a quick test to confirm the voice cloning system is working correctly.
EOF
"$PYTHON_BIN" -m pip show TTS coqui-tts >/dev/null 2>&1 || true
"$VENV_DIR/bin/python" "$WORKDIR/podcast_uret.py" /tmp/podcast_test_script.txt || warn "Test uretimi basarisiz oldu, yukaridaki hata mesajina bakin."

say "Kurulum tamamlandi!"
echo "Sanal ortami aktif etmek icin:  source $VENV_DIR/bin/activate"
echo "Podcast uretmek icin:           python podcast_uret.py scriptler/bu_hafta.txt"
echo "(Bu komutlari $WORKDIR klasorunde calistirin)"
