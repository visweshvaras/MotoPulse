#!/bin/bash
# ==============================================================================
# ESP32-S3 + INMP441 Digital Microphone Control Panel
# Location: /home/vishwa/Documents/hacktivate/mic_test/run_test.sh
# ==============================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PORT="/dev/ttyACM0"
RECORDINGS_DIR="/home/vishwa/Documents/hacktivate/audio_recordings"

# Ensure serial port permission
if [ -e "$PORT" ] && [ ! -w "$PORT" ]; then
    echo "🔑 Fixing serial port permission for $PORT..."
    sudo chmod 666 "$PORT" 2>/dev/null || true
fi

show_menu() {
    clear
    echo "============================================================"
    echo "   🎙️  ESP32-S3 + INMP441 DIGITAL STUDIO CONTROL PANEL      "
    echo "============================================================"
    echo "  1) 🎧 Live Mic Audio Monitor (Hear Live Sound on Speakers + VU Meter)"
    echo "  2) 📊 Live Volume Meter (Terminal Visualizer Only)"
    echo "  3) 📺 Live OLED Spectrum Analyzer (16-Band Visualizer on OLED)"
    echo "  4) 🎯 50cm Near-Field Perimeter Demo (Single-Mic Spatial Gating)"
    echo "  5) 🎵 Record Audio Clip (3 Seconds -> Studio Enhanced MP3 & WAV)"
    echo "  6) 📁 Open Recordings Folder in File Manager"
    echo "  7) 🔊 Play Latest Recording"
    echo "  8) ❌ Exit"
    echo "============================================================"
    echo -n "Select an option [1-8]: "
}

run_live_feed() {
    clear
    echo "Starting Live Mic Audio Monitor... (Press Ctrl+C to stop)"
    python3 "$DIR/live_mic_feed.py"
    echo -e "\nPress Enter to return to menu..."
    read -r
}

run_live() {
    clear
    echo "Starting Live INMP441 Sound Meter... (Press Ctrl+C to stop)"
    python3 "$DIR/test_inmp441_live.py"
    echo -e "\nPress Enter to return to menu..."
    read -r
}

run_oled_spectrum() {
    clear
    echo "Launching OLED Live Spectrum Display... (Press Ctrl+C to stop)"
    python3 "/home/vishwa/Documents/hacktivate/oled_spectrum/live_spectrum_oled.py"
    echo -e "\nPress Enter to return to menu..."
    read -r
}

run_50cm_demo() {
    clear
    echo "Launching 50cm Near-Field Perimeter Gate... (Press Ctrl+C to stop)"
    python3 "/home/vishwa/Documents/hacktivate/near_field_demo/demo_50cm_perimeter.py"
    echo -e "\nPress Enter to return to menu..."
    read -r
}

run_record_3() {
    clear
    echo "Recording 3 seconds of high-fidelity audio..."
    python3 "$DIR/record_inmp441.py" --seconds 3
    echo -e "\nPress Enter to return to menu..."
    read -r
}

open_folder() {
    echo "Opening recordings folder..."
    xdg-open "$RECORDINGS_DIR" 2>/dev/null || nautilus "$RECORDINGS_DIR" 2>/dev/null &
    echo "Folder opened."
    sleep 1
}

play_latest() {
    LATEST=$(ls -t "$RECORDINGS_DIR"/*.mp3 2>/dev/null | head -n 1)
    if [ -n "$LATEST" ]; then
        echo "Playing: $LATEST"
        xdg-open "$LATEST" 2>/dev/null || ffplay -nodisp -autoexit "$LATEST" 2>/dev/null &
    else
        echo "No recordings found yet in $RECORDINGS_DIR."
    fi
    sleep 1
}

case "$1" in
    feed|hear|audio)
        run_live_feed
        exit 0
        ;;
    live|meter|vu)
        run_live
        exit 0
        ;;
    oled|spectrum)
        run_oled_spectrum
        exit 0
        ;;
    gate|near|50cm)
        run_50cm_demo
        exit 0
        ;;
    record|song)
        python3 "$DIR/record_inmp441.py" --seconds 3
        exit 0
        ;;
    folder|open)
        open_folder
        exit 0
        ;;
    play)
        play_latest
        exit 0
        ;;
esac

while true; do
    show_menu
    read -r choice
    case "$choice" in
        1) run_live_feed ;;
        2) run_live ;;
        3) run_oled_spectrum ;;
        4) run_50cm_demo ;;
        5) run_record_3 ;;
        6) open_folder ;;
        7) play_latest ;;
        8|q|Q) 
            echo "Exiting. Happy listening!"
            exit 0
            ;;
        *)
            echo "Invalid choice. Please select 1-8."
            sleep 1
            ;;
    esac
done
