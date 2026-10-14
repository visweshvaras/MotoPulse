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
    echo "  1) 📊 Single Mic Live Volume Meter (Mono)"
    echo "  2) 🎙️🎙️ Dual Mic Stereo Live Meter (Mic 1 Left & Mic 2 Right)"
    echo "  3) 🎧 Live Mic Passthrough (Hear Yourself in Real-Time!)"
    echo "  4) 📺 Live OLED Spectrum Analyzer (16-Band Visualizer on OLED)"
    echo "  5) 🎯 50cm Near-Field Perimeter Gate (Spatial Gating Demo)"
    echo "  6) 🎵 Record Audio Clip (5s, 10s, 30s, or Manual Stop)"
    echo "  7) 📁 Open Recordings Folder in File Manager"
    echo "  8) 🔊 Play Latest Recording"
    echo "  9) ❌ Exit"
    echo "============================================================"
    echo -n "Select an option [1-9]: "
}

run_live() {
    clear
    echo "Starting Live INMP441 Sound Meter... (Press Ctrl+C to stop)"
    python3 "$DIR/test_inmp441_live.py"
    echo -e "\nPress Enter to return to menu..."
    read -r
}

run_dual_live() {
    clear
    echo "Starting Dual-Mic Stereo Sound Meter... (Press Ctrl+C to stop)"
    python3 "$DIR/test_dual_mics_live.py"
    echo -e "\nPress Enter to return to menu..."
    read -r
}

run_mic_passthrough() {
    clear
    echo "============================================================"
    echo "   🎧 LIVE MICROPHONE PASSTHROUGH (HEAR YOURSELF LIVE)      "
    echo "============================================================"
    echo "  1) Mono (Single Mic)"
    echo "  2) Stereo 3D (Mic 1 in Left Ear, Mic 2 in Right Ear!)"
    echo "============================================================"
    echo -n "Choose mode [1 or 2]: "
    read -r m_choice
    clear
    if [ "$m_choice" = "2" ]; then
        python3 "$DIR/live_mic_monitor.py" --stereo
    else
        python3 "$DIR/live_mic_monitor.py"
    fi
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

run_record_menu() {
    clear
    echo "============================================================"
    echo "   🎙️ RECORD AUDIO CLIP TO WAV & MP3                        "
    echo "============================================================"
    echo "  1) Quick 5-Second Clip"
    echo "  2) Full 10-Second Clip"
    echo "  3) Long 30-Second Clip"
    echo "  4) 🔴 Manual Start & Stop (Press Enter when done!)"
    echo "  5) 🎧 Stereo 10-Second Dual-Mic Recording"
    echo "============================================================"
    echo -n "Select recording option [1-5]: "
    read -r r_choice
    clear
    case "$r_choice" in
        1) python3 "$DIR/record_inmp441.py" --seconds 5 ;;
        2) python3 "$DIR/record_inmp441.py" --seconds 10 ;;
        3) python3 "$DIR/record_inmp441.py" --seconds 30 ;;
        4) python3 "$DIR/record_inmp441.py" --manual ;;
        5) python3 "$DIR/record_inmp441.py" --seconds 10 --stereo ;;
        *) python3 "$DIR/record_inmp441.py" --seconds 10 ;;
    esac
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
    LATEST=$(ls -t "$RECORDINGS_DIR"/*.wav 2>/dev/null | head -n 1)
    if [ -n "$LATEST" ]; then
        echo "Playing: $LATEST"
        aplay "$LATEST" 2>/dev/null || ffplay -nodisp -autoexit "$LATEST" 2>/dev/null &
    else
        echo "No recordings found yet in $RECORDINGS_DIR."
    fi
    sleep 1
}

case "$1" in
    live|meter|vu)
        run_live
        exit 0
        ;;
    dual)
        run_dual_live
        exit 0
        ;;
    mic|hear|listen)
        run_mic_passthrough
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
        run_record_menu
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
        1) run_live ;;
        2) run_dual_live ;;
        3) run_mic_passthrough ;;
        4) run_oled_spectrum ;;
        5) run_50cm_demo ;;
        6) run_record_menu ;;
        7) open_folder ;;
        8) play_latest ;;
        9|q|Q) 
            echo "Exiting. Happy listening!"
            exit 0
            ;;
        *)
            echo "Invalid choice. Please select 1-9."
            sleep 1
            ;;
    esac
done
