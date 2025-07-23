import sys
import os
import random
import pygame
from mutagen.mp3 import MP3
import subprocess

from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QListWidget, QLineEdit,
    QVBoxLayout, QHBoxLayout, QLabel, QSlider, QFileDialog, QStyle, QMessageBox
)
import threading
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QBrush

class MusicPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Adams hellish dnd player")
        self.setMinimumSize(750, 620)
        pygame.mixer.init()

        # Widgets
        self.folders_list = QListWidget()
        self.tracks_list = QListWidget()
        self.queue_list = QListWidget()
        self.text_input = QLineEdit()
        self.download_button = QPushButton("📥 Download from YouTube")

        self.current_folder = os.getcwd()

        self.play_pause_button = QPushButton("▶ / ⏸")
        self.next_button = QPushButton("⏭ Next")
        self.shuffle_button = QPushButton("🔀 Shuffle")
        self.loop_button = QPushButton("🔁 Loop: OFF")
        self.add_to_queue_button = QPushButton("➕ Add to Queue")

        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 1000)
        self.slider_moving = False

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        pygame.mixer.music.set_volume(0.5)

        self.mute_button = QPushButton("🔊")
        self.muted = False

        self.track_label = QLabel("🎵 No track loaded")
        self.track_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setFont(QFont("Consolas", 11))

        

        # Playback state
        self.current_playlist = []
        self.current_index = -1
        self.current_track_length = 0
        self.loop_enabled = False
        self.seek_offset = 0

        # Timer for UI updates
        self.timer = QTimer()
        self.timer.setInterval(500)

        self.setup_ui()
        self.load_folders()
        self.connect_signals()
        self.set_style()

    def setup_ui(self):
        layout = QVBoxLayout()

        layout.addWidget(QLabel("🎧 Folders:"))
        layout.addWidget(self.folders_list)
        layout.addWidget(QLabel("🎼 Audio Files:"))
        layout.addWidget(self.tracks_list)
        layout.addWidget(self.add_to_queue_button)
        layout.addWidget(QLabel("🎶 Queue:"))
        layout.addWidget(self.queue_list)

        buttons_layout = QHBoxLayout()
        for btn in (self.play_pause_button, self.next_button, self.shuffle_button, self.loop_button):
            buttons_layout.addWidget(btn)
        layout.addLayout(buttons_layout)

        layout.addWidget(self.track_label)
        layout.addWidget(self.position_slider)
        layout.addWidget(self.time_label)

        volume_layout = QHBoxLayout()
        volume_layout.addWidget(self.mute_button)
        volume_layout.addWidget(self.volume_slider)
        layout.addLayout(volume_layout)

        layout.addWidget(QLabel("📥 YouTube URL:"))
        layout.addWidget(self.text_input)
        layout.addWidget(self.download_button)
        self.status_label = QLabel("Idle")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def set_style(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#121212"))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        self.setPalette(palette)
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #eee;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            QPushButton {
                background-color: #282828;
                border: none;
                border-radius: 6px;
                padding: 8px 14px;
                color: #eee;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3c3c3c;
            }
            QListWidget, QLineEdit, QSlider {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 5px;
                color: #ddd;
                font-size: 13px;
            }
            QListWidget::item:selected {
                background-color: #4a90e2;
                color: white;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background: #333;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4a90e2;
                width: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
            QLabel {
                color: #bbb;
            }
        """)

    def load_folders(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
        self.folders_list.clear()
        self.folders_list.addItems(folders)

    def connect_signals(self):
        self.folders_list.itemClicked.connect(self.load_audio_files)
        self.tracks_list.itemDoubleClicked.connect(self.play_selected_audio)
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        self.next_button.clicked.connect(self.play_next)
        self.shuffle_button.clicked.connect(self.shuffle_playlist)
        self.download_button.clicked.connect(self.download_from_youtube)
        self.loop_button.clicked.connect(self.toggle_loop)
        self.add_to_queue_button.clicked.connect(self.add_selected_to_queue)
        self.position_slider.sliderPressed.connect(self.slider_pressed)
        self.position_slider.sliderReleased.connect(self.slider_released)
        self.volume_slider.valueChanged.connect(self.change_volume)
        self.timer.timeout.connect(self.update_slider)
        self.mute_button.clicked.connect(self.toggle_mute)

    def load_audio_files(self, item):
        folder = item.text()

        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, folder)
        self.current_folder = path
        files = [f for f in os.listdir(path) if f.lower().endswith(('.mp3', '.wav', '.ogg'))]
        self.tracks_list.clear()
        self.queue_list.clear()
        self.tracks_list.addItems(files)
        self.current_playlist = [os.path.join(path, f) for f in files]
        self.queue_list.addItems(files)
        self.current_index = -1

    def add_selected_to_queue(self):
        selected = self.tracks_list.currentItem()
        if selected:
            file_name = selected.text()
            # Find full path for selected file
            for path in self.current_playlist:
                if path.endswith(file_name):
                    self.current_playlist.append(path)
                    self.queue_list.addItem(file_name)
                    break

    def play_selected_audio(self, item):
        index = self.tracks_list.currentRow()
        self.play_audio(index)

    def play_audio(self, index):
        if 0 <= index < len(self.current_playlist):
            self.current_index = index
            file_path = self.current_playlist[index]
            try:
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
                self.seek_offset = 0  # Reset seek offset for new track
                self.track_label.setText(f"🎵 {os.path.basename(file_path)}")
                self.current_track_length = self.get_track_length(file_path)
                self.timer.start()
                self.highlight_current_queue_item()
            except Exception as e:
                self.track_label.setText(f"Error loading: {e}")

    def highlight_current_queue_item(self):
        # Clear all highlights
        for i in range(self.queue_list.count()):
            item = self.queue_list.item(i)
            item.setBackground(QBrush(Qt.GlobalColor.transparent))
            item.setForeground(QBrush(Qt.GlobalColor.white))
        # Highlight current
        if 0 <= self.current_index < self.queue_list.count():
            current_item = self.queue_list.item(self.current_index)
            current_item.setBackground(QBrush(QColor("#4a90e2")))
            current_item.setForeground(QBrush(Qt.GlobalColor.white))
            self.queue_list.scrollToItem(current_item)

    def toggle_play_pause(self):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
        else:
            if self.current_index == -1 and self.current_playlist:
                self.play_audio(0)
            else:
                pygame.mixer.music.unpause()

    def play_next(self):
        if self.current_playlist:
            if self.loop_enabled:
                self.current_index = (self.current_index + 1) % len(self.current_playlist)
            else:
                self.current_index += 1
                if self.current_index >= len(self.current_playlist):
                    self.timer.stop()
                    return
            self.play_audio(self.current_index)

    def shuffle_playlist(self):
        if self.current_playlist:
            random.shuffle(self.current_playlist)
            self.queue_list.clear()
            self.queue_list.addItems([os.path.basename(p) for p in self.current_playlist])
            self.current_index = 0
            self.play_audio(self.current_index)

    def toggle_loop(self):
        self.loop_enabled = not self.loop_enabled
        self.loop_button.setText(f"🔁 Loop: {'ON' if self.loop_enabled else 'OFF'}")

    def download_from_youtube(self):
        url = str(self.text_input.text())
        #if not url or not self.current_folder:
            #QMessageBox.warning(self, "Missing Info", "Please enter a URL and select a folder.")
            #return
        print("Url was: ", url)
        print(self.current_folder)

        self.status_label.setText("⏬ Downloading...")
        self.status_label.setStyleSheet("color: blue;")

        def run_download():
            try:
                cmd = [
                    os.path.join(os.getcwd(), "yt-dlp.exe"),
                    "-x",
                    "--audio-format", "mp3",
                    "-o", os.path.join(self.current_folder, "%(title)s.%(ext)s"),
                    url
                ]
                print(cmd)
                subprocess.run(cmd, check=True)
                self.status_label.setText("✅ Download complete!")
                self.status_label.setStyleSheet("color: green;")
            except Exception as e:
                self.status_label.setText("❌ Download failed.")
                self.status_label.setStyleSheet("color: red;")
                print(f"Download error: {e}")

        threading.Thread(target=run_download, daemon=True).start()
        self.load_folders()

    def update_slider(self):
        if not self.slider_moving:
            # get_pos() returns time since play() was called. We must add our seek offset.
            pos_since_play = pygame.mixer.music.get_pos() / 1000.0
            if pos_since_play < 0:  # Can be -1 if music is not playing
                pos_since_play = 0
            
            pos = self.seek_offset + pos_since_play
            percent = int((pos / self.current_track_length) * 1000)
            self.position_slider.setValue(min(percent, 1000))
            self.update_time_label(pos, self.current_track_length)

            if pos >= self.current_track_length - 0.5:  # Use a small buffer
                self.play_next()
        else:
            print("otherwise")
            #this is our slider condition
            pos_since_play = self.seek_offset
            pos = self.seek_offset
            percent = int((pos / self.current_track_length) * 1000)
            self.position_slider.setValue(min(percent, 1000))
            self.update_time_label(pos, self.current_track_length)
            if pos >= self.current_track_length - 0.5:  # Use a small buffer
                self.play_next()


    def update_time_label(self, pos_sec, total_sec):
        def format_time(s):
            m, s = divmod(int(s), 60)
            return f"{m:02d}:{s:02d}"
        self.time_label.setText(f"{format_time(pos_sec)} / {format_time(total_sec)}")

    def slider_pressed(self):
        self.slider_moving = True

    def slider_released(self):
        # Check if a track is loaded and has a valid index
        if self.current_track_length and self.current_index != -1:
            seek_time = (self.position_slider.value() / 1000.0) * self.current_track_length
            # No need to reload the file. Just play from the new position.
            # This prevents a stutter/glitch when seeking.
            pygame.mixer.music.play(start=seek_time)
            self.seek_offset = seek_time
            self.slider_moving = False
            self.update_slider()

    def change_volume(self, value):
        if not self.muted:
            pygame.mixer.music.set_volume(value / 100.0)

    def toggle_mute(self):
        if self.muted:
            self.muted = False
            self.mute_button.setText("🔊")
            pygame.mixer.music.set_volume(self.volume_slider.value() / 100.0)
        else:
            self.muted = True
            self.mute_button.setText("🔇")
            pygame.mixer.music.set_volume(0)

    def get_track_length(self, file_path):
        try:
            if file_path.lower().endswith(".mp3"):
                audio = MP3(file_path)
                return audio.info.length
        except:
            return 0
        return 0

if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = MusicPlayer()
    player.show()
    sys.exit(app.exec())
