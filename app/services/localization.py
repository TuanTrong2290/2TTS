# -*- coding: utf-8 -*-
"""Localization service for multi-language support"""
from typing import Dict, Optional
from pathlib import Path
import json


# Vietnamese translations
TRANSLATIONS_VI = {
    # Main Window
    "app_title": "2TTS - Chuyển văn bản thành giọng nói",
    "file": "Tệp",
    "edit": "Chỉnh sửa",
    "tools": "Công cụ",
    "help": "Trợ giúp",
    
    # Drop Zone
    "drop_files_title": "Kéo thả tệp hoặc thư mục vào đây",
    "drop_files_subtitle": "Hỗ trợ: .srt, .txt, .docx",
    
    # Table columns
    "col_index": "#",
    "col_text": "Văn bản",
    "col_voice": "Giọng nói",
    "col_model": "Mô hình",
    "col_status": "Trạng thái",
    "col_duration": "Thời lượng",
    "col_language": "Ngôn ngữ",
    
    # Voice settings additional
    "similarity": "Độ tương đồng",
    "v3_audio_tags_hint": "💡 Sử dụng thẻ âm thanh: [laughs], [whispers], [sarcastic], v.v.",
    
    # Progress widget
    "lines_progress": "{completed}/{total} dòng",
    "elapsed": "Đã chạy",
    "eta": "Còn lại",
    "ready": "Sẵn sàng",
    
    # Filter widget
    "search_placeholder": "Tìm kiếm văn bản...",
    "all_status": "Tất cả trạng thái",
    "clear": "Xóa",
    
    # Thread status
    "active_threads": "Hoạt động: {active} / {total}",
    
    # Buttons
    "join_mp3": "Ghép MP3",
    "generate_srt": "Tạo SRT",
    "apply_to_selected": "Áp dụng cho đã chọn",
    "apply_to_all": "Áp dụng cho tất cả",
    "loop_count_label": "Số lần lặp (0=∞)",
    "export_log": "Xuất nhật ký",
    
    # File menu
    "new_project": "Dự án mới",
    "open_project": "Mở dự án",
    "save_project": "Lưu dự án",
    "save_project_as": "Lưu dự án thành...",
    "import_files": "Nhập tệp",
    "export_srt": "Xuất SRT",
    "export_audio": "Xuất âm thanh",
    "exit": "Thoát",
    
    # Edit menu
    "undo": "Hoàn tác",
    "redo": "Làm lại",
    "select_all": "Chọn tất cả",
    "delete_selected": "Xóa đã chọn",
    "clear_all": "Xóa tất cả",
    
    # Tools menu
    "api_keys": "Quản lý API Key",
    "proxies": "Quản lý Proxy",
    "voice_library": "Thư viện giọng nói",
    "voice_assignment": "Gán giọng nói",
    "audio_processing": "Xử lý âm thanh",
    "presets": "Quản lý Preset",
    "analytics": "Thống kê",
    "settings": "Cài đặt",
    
    # Help menu
    "check_updates": "Kiểm tra cập nhật",
    "documentation": "Tài liệu",
    "about": "Giới thiệu",
    
    # Toolbar
    "start": "Bắt đầu",
    "pause": "Tạm dừng",
    "resume": "Tiếp tục",
    "stop": "Dừng",
    "open_folder": "Mở thư mục",
    
    # Main panels
    "drop_files_here": "Kéo thả tệp vào đây",
    "or_click_to_browse": "hoặc nhấp để duyệt",
    "supported_formats": "Hỗ trợ: TXT, SRT, DOCX",
    "voice_settings": "Cài đặt giọng nói",
    "default_voice": "Giọng mặc định",
    "select_voice": "Chọn giọng nói...",
    "stability": "Độ ổn định",
    "clarity": "Độ rõ ràng",
    "style": "Phong cách",
    "speed": "Tốc độ",
    "model": "Mô hình",
    "speaker_boost": "Tăng cường giọng",
    
    # Processing settings
    "processing_settings": "Cài đặt xử lý",
    "threads": "Luồng",
    "loop_mode": "Chế độ lặp",
    "loop_count": "Số lần lặp",
    "output_folder": "Thư mục xuất",
    "browse": "Duyệt",
    
    # Table headers
    "index": "STT",
    "text": "Văn bản",
    "voice": "Giọng nói",
    "status": "Trạng thái",
    "duration": "Thời lượng",
    "error": "Lỗi",
    
    # Status values
    "pending": "Chờ xử lý",
    "processing": "Đang xử lý",
    "done": "Hoàn thành",
    "error_status": "Lỗi",
    
    # Progress
    "progress": "Tiến độ",
    "completed": "Hoàn thành",
    "failed": "Thất bại",
    "remaining": "Còn lại",
    "elapsed_time": "Thời gian",
    "estimated_time": "Ước tính còn",
    
    # Credits
    "credits": "Tín dụng",
    "total_credits": "Tổng tín dụng",
    "used": "Đã dùng",
    "remaining_credits": "Còn lại",
    "refresh": "Làm mới",
    
    # Buttons
    "add": "Thêm",
    "remove": "Xóa",
    "save": "Lưu",
    "cancel": "Hủy",
    "close": "Đóng",
    "ok": "OK",
    "yes": "Có",
    "no": "Không",
    "apply": "Áp dụng",
    "reset": "Đặt lại",
    "import": "Nhập",
    "export": "Xuất",
    "validate": "Xác thực",
    "validate_all": "Xác thực tất cả",
    "retry": "Thử lại",
    "retry_failed": "Thử lại thất bại",
    "play": "Phát",
    "stop_playing": "Dừng phát",
    "preview": "Xem trước",
    "split": "Tách",
    "merge": "Gộp",
    "copy": "Sao chép",
    "paste": "Dán",
    "cut": "Cắt",
    
    # Dialogs
    "api_key_manager": "Quản lý API Key",
    "add_api_key": "Thêm API Key",
    "api_key": "API Key",
    "api_key_name": "Tên",
    "proxy_manager": "Quản lý Proxy",
    "add_proxy": "Thêm Proxy",
    "host": "Máy chủ",
    "port": "Cổng",
    "username": "Tên đăng nhập",
    "password": "Mật khẩu",
    "proxy_type": "Loại Proxy",
    "enabled": "Bật",
    "disabled": "Tắt",
    
    # Voice Library
    "voice_library_title": "Thư viện giọng nói",
    "your_voices": "Giọng của bạn",
    "library_voices": "Thư viện giọng",
    "search_voices": "Tìm kiếm giọng nói...",
    "add_by_id": "Thêm bằng ID",
    "select": "Chọn",
    "voice_id": "ID Giọng nói",
    "voice_name": "Tên giọng nói",
    "category": "Danh mục",
    "language": "Ngôn ngữ",
    "accent": "Giọng địa phương",
    "gender": "Giới tính",
    "age": "Độ tuổi",
    "cloned": "Đã nhân bản",
    
    # Settings Dialog
    "settings_title": "Cài đặt",
    "processing": "Xử lý",
    "thread_count": "Số luồng",
    "max_retries": "Số lần thử lại tối đa",
    "request_delay": "Độ trễ yêu cầu",
    "text_splitting": "Tách văn bản",
    "auto_split_long_text": "Tự động tách văn bản dài",
    "max_characters": "Số ký tự tối đa",
    "split_delimiters": "Ký tự phân cách",
    "audio": "Âm thanh",
    "silence_gap": "Khoảng lặng",
    "appearance": "Giao diện",
    "theme": "Chủ đề",
    "system": "Hệ thống",
    "dark": "Tối",
    "light": "Sáng",
    "automation": "Tự động hóa",
    "auto_start_on_launch": "Tự động bắt đầu khi khởi động",
    "import_export": "Nhập/Xuất",
    "import_settings": "Nhập cài đặt",
    "export_settings": "Xuất cài đặt",
    
    # Vietnamese TTS Settings
    "vietnamese_tts": "TTS Tiếng Việt (Độ chính xác thanh điệu)",
    "enable_preprocessing": "Bật tiền xử lý",
    "max_phrase_words": "Số từ tối đa mỗi cụm",
    "add_micro_pauses": "Thêm ngắt nghỉ nhỏ",
    "pause_interval": "Khoảng cách ngắt",
    
    # Pause Settings
    "pause_settings": "Cài đặt ngắt nghỉ",
    "enable_pauses": "Bật ngắt nghỉ",
    "short_pause": "Ngắt ngắn",
    "long_pause": "Ngắt dài",
    "short_pause_punctuation": "Dấu câu ngắt ngắn",
    "long_pause_punctuation": "Dấu câu ngắt dài",
    
    # Filter
    "filter": "Lọc",
    "search": "Tìm kiếm",
    "all": "Tất cả",
    "filter_by_status": "Lọc theo trạng thái",
    
    # Log
    "log": "Nhật ký",
    "clear_log": "Xóa nhật ký",
    
    # Messages
    "confirm_delete": "Xác nhận xóa",
    "confirm_delete_lines": "Bạn có chắc muốn xóa {count} dòng?",
    "confirm_clear_all": "Bạn có chắc muốn xóa tất cả các dòng?",
    "confirm_exit": "Xác nhận thoát",
    "confirm_exit_processing": "Đang xử lý. Bạn có chắc muốn thoát?",
    "unsaved_changes": "Có thay đổi chưa lưu. Bạn có muốn lưu không?",
    "project_saved": "Dự án đã được lưu",
    "project_loaded": "Dự án đã được tải",
    "import_success": "Đã nhập {count} dòng thành công",
    "import_error": "Lỗi nhập tệp",
    "export_success": "Xuất thành công",
    "export_error": "Lỗi xuất",
    "no_lines": "Không có dòng nào để xử lý",
    "no_voice_selected": "Chưa chọn giọng nói",
    "no_api_keys": "Chưa có API key. Vui lòng thêm API key trước.",
    "processing_started": "Bắt đầu xử lý {count} dòng",
    "processing_completed": "Xử lý hoàn tất",
    "processing_stopped": "Đã dừng xử lý",
    "all_keys_exhausted": "Tất cả API key đã hết hạn mức",
    "rate_limit_hit": "Đạt giới hạn tốc độ, đang chuyển key...",
    "connection_error": "Lỗi kết nối",
    "invalid_api_key": "API key không hợp lệ",
    "success": "Thành công",
    "error": "Lỗi",
    "warning": "Cảnh báo",
    "info": "Thông tin",
    
    # About
    "about_title": "Giới thiệu 2TTS",
    "about_text": "2TTS - Công cụ chuyển văn bản thành giọng nói ElevenLabs\n\n"
                  "Công cụ mạnh mẽ để chuyển đổi hàng loạt văn bản thành giọng nói "
                  "sử dụng API ElevenLabs.\n\n"
                  "Tính năng:\n"
                  "- Xử lý đa luồng\n"
                  "- Hỗ trợ nhiều API key\n"
                  "- Hỗ trợ Proxy\n"
                  "- Nhập/xuất SRT\n"
                  "- Thư viện giọng nói",
    
    # Thread Status
    "thread_status": "Trạng thái luồng",
    "idle": "Rảnh",
    "working": "Đang làm việc",
    "waiting": "Đang chờ",
    
    # Cloud
    "cloud_projects": "Dự án đám mây",
    "sync_to_cloud": "Đồng bộ lên đám mây",
    "sync_from_cloud": "Đồng bộ từ đám mây",
    "cloud_config": "Cấu hình đám mây",
    "refresh_from_cloud": "Làm mới từ đám mây",
    
    # Preset
    "preset_manager": "Quản lý Preset",
    "save_as_preset": "Lưu thành Preset",
    "load_preset": "Tải Preset",
    "preset_name": "Tên Preset",
    
    # Audio Processing
    "audio_processing_title": "Xử lý âm thanh",
    "normalize_audio": "Chuẩn hóa âm thanh",
    "remove_silence": "Xóa khoảng lặng",
    "add_fade": "Thêm hiệu ứng fade",
    "fade_in": "Fade vào",
    "fade_out": "Fade ra",
    "concatenate": "Nối âm thanh",
    
    # Updates
    "update_available": "Có bản cập nhật mới",
    "current_version": "Phiên bản hiện tại",
    "latest_version": "Phiên bản mới nhất",
    "download_update": "Tải cập nhật",
    "no_updates": "Bạn đang dùng phiên bản mới nhất",
    
    # Analytics
    "analytics_title": "Thống kê",
    "total_processed": "Tổng đã xử lý",
    "total_characters": "Tổng ký tự",
    "total_duration": "Tổng thời lượng",
    "success_rate": "Tỷ lệ thành công",
    
    # Transcription (Speech-to-Text)
    "transcribe": "Chuyển giọng nói",
    "transcribe_tab": "Chuyển giọng nói",
    "transcribe_audio": "Chuyển âm thanh thành văn bản",
    "transcription_settings": "Cài đặt chuyển đổi",
    "transcription_queue": "Hàng đợi chuyển đổi",
    "transcription_result": "Kết quả chuyển đổi",
    "drop_media_here": "Kéo thả tệp âm thanh/video vào đây",
    "drop_media_or_browse": "hoặc nhấp để duyệt",
    "supported_media": "MP3, WAV, M4A, MP4, MKV, v.v.",
    "auto_detect": "Tự động nhận diện",
    "identify_speakers": "Nhận diện người nói (Diarization)",
    "expected_speakers": "Số người nói dự kiến",
    "speakers": "Người nói",
    "edit_speakers": "Sửa người nói",
    "edit_speaker_names": "Sửa tên người nói",
    "assign_speaker_names": "Gán tên cho người nói:",
    "speaker": "Người nói",
    "clear_completed": "Xóa đã hoàn thành",
    "transcribing": "Đang chuyển đổi",
    "seeking_to": "Đang chuyển đến",
    "no_files_in_queue": "Không có tệp trong hàng đợi",
    "no_transcription_result": "Không có kết quả để xuất",
    "export_transcription": "Xuất bản chuyển đổi",
    "file_too_large": "Tệp quá lớn",
    "unsupported_format": "Định dạng không hỗ trợ",
    "job_completed": "Hoàn thành công việc",
    "job_failed": "Công việc thất bại",
    "no_result": "Không có kết quả",
    "segments": "đoạn",
    "retry_transcription": "Thử lại chuyển đổi",
    "file": "Tệp",
    "size": "Kích thước",
    
    # Misc
    "loading": "Đang tải...",
    "please_wait": "Vui lòng chờ...",
    "no_data": "Không có dữ liệu",
    "unknown": "Không xác định",
    "none": "Không có",
    "line": "Dòng",
    "lines": "dòng",
    "character": "ký tự",
    "characters": "ký tự",
    "second": "giây",
    "seconds": "giây",
    "minute": "phút",
    "minutes": "phút",
    "hour": "giờ",
    "hours": "giờ",
}

# English translations (default)
TRANSLATIONS_EN = {
    # Main Window
    "app_title": "2TTS - ElevenLabs Text-To-Speech",
    "file": "File",
    "edit": "Edit",
    "tools": "Tools",
    "help": "Help",
    
    # Drop Zone
    "drop_files_title": "Drop files or folders here",
    "drop_files_subtitle": "Supported: .srt, .txt, .docx",
    
    # Table columns
    "col_index": "#",
    "col_text": "Text",
    "col_voice": "Voice",
    "col_model": "Model",
    "col_status": "Status",
    "col_duration": "Duration",
    "col_language": "Language",
    
    # Voice settings additional
    "similarity": "Similarity",
    "v3_audio_tags_hint": "💡 Use audio tags: [laughs], [whispers], [sarcastic], etc.",
    
    # Progress widget
    "lines_progress": "{completed}/{total} lines",
    "elapsed": "Elapsed",
    "eta": "ETA",
    "ready": "Ready",
    
    # Filter widget
    "search_placeholder": "Search text...",
    "all_status": "All Status",
    "clear": "Clear",
    
    # Thread status
    "active_threads": "Active: {active} / {total}",
    
    # Buttons
    "join_mp3": "Join MP3",
    "generate_srt": "Generate SRT",
    "apply_to_selected": "Apply to Selected",
    "apply_to_all": "Apply to All",
    "loop_count_label": "Loop count (0=∞)",
    "export_log": "Export Log",
    
    # File menu
    "new_project": "New Project",
    "open_project": "Open Project",
    "save_project": "Save Project",
    "save_project_as": "Save Project As...",
    "import_files": "Import Files",
    "export_srt": "Export SRT",
    "export_audio": "Export Audio",
    "exit": "Exit",
    
    # Edit menu
    "undo": "Undo",
    "redo": "Redo",
    "select_all": "Select All",
    "delete_selected": "Delete Selected",
    "clear_all": "Clear All",
    
    # Tools menu
    "api_keys": "API Keys",
    "proxies": "Proxies",
    "voice_library": "Voice Library",
    "voice_assignment": "Voice Assignment",
    "audio_processing": "Audio Processing",
    "presets": "Presets",
    "analytics": "Analytics",
    "settings": "Settings",
    
    # Help menu
    "check_updates": "Check for Updates",
    "documentation": "Documentation",
    "about": "About",
    
    # Toolbar
    "start": "Start",
    "pause": "Pause",
    "resume": "Resume",
    "stop": "Stop",
    "open_folder": "Open Folder",
    
    # Main panels
    "drop_files_here": "Drop files here",
    "or_click_to_browse": "or click to browse",
    "supported_formats": "Supported: TXT, SRT, DOCX",
    "voice_settings": "Voice Settings",
    "default_voice": "Default Voice",
    "select_voice": "Select voice...",
    "stability": "Stability",
    "clarity": "Clarity",
    "style": "Style",
    "speed": "Speed",
    "model": "Model",
    "speaker_boost": "Speaker Boost",
    
    # Processing settings
    "processing_settings": "Processing Settings",
    "threads": "Threads",
    "loop_mode": "Loop Mode",
    "loop_count": "Loop Count",
    "output_folder": "Output Folder",
    "browse": "Browse",
    
    # Table headers
    "index": "#",
    "text": "Text",
    "voice": "Voice",
    "status": "Status",
    "duration": "Duration",
    "error": "Error",
    
    # Status values
    "pending": "Pending",
    "processing": "Processing",
    "done": "Done",
    "error_status": "Error",
    
    # Progress
    "progress": "Progress",
    "completed": "Completed",
    "failed": "Failed",
    "remaining": "Remaining",
    "elapsed_time": "Elapsed",
    "estimated_time": "Estimated",
    
    # Credits
    "credits": "Credits",
    "total_credits": "Total Credits",
    "used": "Used",
    "remaining_credits": "Remaining",
    "refresh": "Refresh",
    
    # Buttons
    "add": "Add",
    "remove": "Remove",
    "save": "Save",
    "cancel": "Cancel",
    "close": "Close",
    "ok": "OK",
    "yes": "Yes",
    "no": "No",
    "apply": "Apply",
    "reset": "Reset",
    "import": "Import",
    "export": "Export",
    "validate": "Validate",
    "validate_all": "Validate All",
    "retry": "Retry",
    "retry_failed": "Retry Failed",
    "play": "Play",
    "stop_playing": "Stop",
    "preview": "Preview",
    "split": "Split",
    "merge": "Merge",
    "copy": "Copy",
    "paste": "Paste",
    "cut": "Cut",
    
    # Dialogs
    "api_key_manager": "API Key Manager",
    "add_api_key": "Add API Key",
    "api_key": "API Key",
    "api_key_name": "Name",
    "proxy_manager": "Proxy Manager",
    "add_proxy": "Add Proxy",
    "host": "Host",
    "port": "Port",
    "username": "Username",
    "password": "Password",
    "proxy_type": "Proxy Type",
    "enabled": "Enabled",
    "disabled": "Disabled",
    
    # Voice Library
    "voice_library_title": "Voice Library",
    "your_voices": "Your Voices",
    "library_voices": "Library Voices",
    "search_voices": "Search voices...",
    "add_by_id": "Add by ID",
    "select": "Select",
    "voice_id": "Voice ID",
    "voice_name": "Voice Name",
    "category": "Category",
    "language": "Language",
    "accent": "Accent",
    "gender": "Gender",
    "age": "Age",
    "cloned": "Cloned",
    
    # Settings Dialog
    "settings_title": "Settings",
    "processing": "Processing",
    "thread_count": "Thread Count",
    "max_retries": "Max Retries",
    "request_delay": "Request Delay",
    "text_splitting": "Text Splitting",
    "auto_split_long_text": "Auto-split long text",
    "max_characters": "Max characters",
    "split_delimiters": "Split delimiters",
    "audio": "Audio",
    "silence_gap": "Silence gap",
    "appearance": "Appearance",
    "theme": "Theme",
    "system": "System",
    "dark": "Dark",
    "light": "Light",
    "automation": "Automation",
    "auto_start_on_launch": "Auto-start on launch",
    "import_export": "Import/Export",
    "import_settings": "Import Settings",
    "export_settings": "Export Settings",
    
    # Vietnamese TTS Settings
    "vietnamese_tts": "Vietnamese TTS (Tone Accuracy)",
    "enable_preprocessing": "Enable preprocessing",
    "max_phrase_words": "Max phrase words",
    "add_micro_pauses": "Add micro-pauses",
    "pause_interval": "Pause interval",
    
    # Pause Settings
    "pause_settings": "Pause Settings",
    "enable_pauses": "Enable pauses",
    "short_pause": "Short pause",
    "long_pause": "Long pause",
    "short_pause_punctuation": "Short pause punctuation",
    "long_pause_punctuation": "Long pause punctuation",
    
    # Filter
    "filter": "Filter",
    "search": "Search",
    "all": "All",
    "filter_by_status": "Filter by status",
    
    # Log
    "log": "Log",
    "clear_log": "Clear Log",
    
    # Messages
    "confirm_delete": "Confirm Delete",
    "confirm_delete_lines": "Are you sure you want to delete {count} lines?",
    "confirm_clear_all": "Are you sure you want to clear all lines?",
    "confirm_exit": "Confirm Exit",
    "confirm_exit_processing": "Processing in progress. Are you sure you want to exit?",
    "unsaved_changes": "You have unsaved changes. Do you want to save?",
    "project_saved": "Project saved",
    "project_loaded": "Project loaded",
    "import_success": "Successfully imported {count} lines",
    "import_error": "Import error",
    "export_success": "Export successful",
    "export_error": "Export error",
    "no_lines": "No lines to process",
    "no_voice_selected": "No voice selected",
    "no_api_keys": "No API keys. Please add an API key first.",
    "processing_started": "Started processing {count} lines",
    "processing_completed": "Processing completed",
    "processing_stopped": "Processing stopped",
    "all_keys_exhausted": "All API keys exhausted",
    "rate_limit_hit": "Rate limit hit, rotating key...",
    "connection_error": "Connection error",
    "invalid_api_key": "Invalid API key",
    "success": "Success",
    "error": "Error",
    "warning": "Warning",
    "info": "Info",
    
    # About
    "about_title": "About 2TTS",
    "about_text": "2TTS - ElevenLabs Text-To-Speech Tool\n\n"
                  "A powerful tool for batch text-to-speech conversion "
                  "using the ElevenLabs API.\n\n"
                  "Features:\n"
                  "- Multi-threaded processing\n"
                  "- Multiple API key support\n"
                  "- Proxy support\n"
                  "- SRT import/export\n"
                  "- Voice library",
    
    # Thread Status
    "thread_status": "Thread Status",
    "idle": "Idle",
    "working": "Working",
    "waiting": "Waiting",
    
    # Cloud
    "cloud_projects": "Cloud Projects",
    "sync_to_cloud": "Sync to Cloud",
    "sync_from_cloud": "Sync from Cloud",
    "cloud_config": "Cloud Config",
    "refresh_from_cloud": "Refresh from Cloud",
    
    # Preset
    "preset_manager": "Preset Manager",
    "save_as_preset": "Save as Preset",
    "load_preset": "Load Preset",
    "preset_name": "Preset Name",
    
    # Audio Processing
    "audio_processing_title": "Audio Processing",
    "normalize_audio": "Normalize Audio",
    "remove_silence": "Remove Silence",
    "add_fade": "Add Fade",
    "fade_in": "Fade In",
    "fade_out": "Fade Out",
    "concatenate": "Concatenate",
    
    # Updates
    "update_available": "Update Available",
    "current_version": "Current Version",
    "latest_version": "Latest Version",
    "download_update": "Download Update",
    "no_updates": "You are using the latest version",
    
    # Analytics
    "analytics_title": "Analytics",
    "total_processed": "Total Processed",
    "total_characters": "Total Characters",
    "total_duration": "Total Duration",
    "success_rate": "Success Rate",
    
    # Transcription (Speech-to-Text)
    "transcribe": "Transcribe",
    "transcribe_tab": "Transcribe",
    "transcribe_audio": "Transcribe Audio",
    "transcription_settings": "Transcription Settings",
    "transcription_queue": "Transcription Queue",
    "transcription_result": "Transcription Result",
    "drop_media_here": "Drop audio/video files here",
    "drop_media_or_browse": "or click to browse",
    "supported_media": "MP3, WAV, M4A, MP4, MKV, etc.",
    "auto_detect": "Auto-detect",
    "identify_speakers": "Identify Speakers (Diarization)",
    "expected_speakers": "Expected Speakers",
    "speakers": "Speakers",
    "edit_speakers": "Edit Speakers",
    "edit_speaker_names": "Edit Speaker Names",
    "assign_speaker_names": "Assign custom names to speakers:",
    "speaker": "Speaker",
    "clear_completed": "Clear Completed",
    "transcribing": "Transcribing",
    "seeking_to": "Seeking to",
    "no_files_in_queue": "No files in queue",
    "no_transcription_result": "No transcription result to export",
    "export_transcription": "Export Transcription",
    "file_too_large": "File too large",
    "unsupported_format": "Unsupported format",
    "job_completed": "Job completed",
    "job_failed": "Job failed",
    "no_result": "No result",
    "segments": "segments",
    "retry_transcription": "Retry Transcription",
    "file": "File",
    "size": "Size",
    
    # Misc
    "loading": "Loading...",
    "please_wait": "Please wait...",
    "no_data": "No data",
    "unknown": "Unknown",
    "none": "None",
    "line": "line",
    "lines": "lines",
    "character": "character",
    "characters": "characters",
    "second": "second",
    "seconds": "seconds",
    "minute": "minute",
    "minutes": "minutes",
    "hour": "hour",
    "hours": "hours",
}

TRANSLATIONS = {
    "en": TRANSLATIONS_EN,
    "vi": TRANSLATIONS_VI,
}

LANGUAGE_NAMES = {
    "en": "English",
    "vi": "Tiếng Việt",
}


class Localization:
    """Singleton class for managing translations"""
    
    _instance: Optional['Localization'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._current_language = "en"
        self._translations = TRANSLATIONS
    
    def set_language(self, lang_code: str):
        """Set the current language"""
        if lang_code in self._translations:
            self._current_language = lang_code
    
    def get_language(self) -> str:
        """Get the current language code"""
        return self._current_language
    
    def get_available_languages(self) -> Dict[str, str]:
        """Get available languages with their display names"""
        return LANGUAGE_NAMES.copy()
    
    def tr(self, key: str, **kwargs) -> str:
        """
        Translate a key to the current language.
        Supports format strings with {placeholder} syntax.
        """
        translations = self._translations.get(self._current_language, TRANSLATIONS_EN)
        text = translations.get(key, TRANSLATIONS_EN.get(key, key))
        
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass
        
        return text
    
    def __call__(self, key: str, **kwargs) -> str:
        """Shorthand for tr()"""
        return self.tr(key, **kwargs)


# Global instance
_localization = None


def get_localization() -> Localization:
    """Get the global localization instance"""
    global _localization
    if _localization is None:
        _localization = Localization()
    return _localization


def tr(key: str, **kwargs) -> str:
    """Convenience function for translation"""
    return get_localization().tr(key, **kwargs)


def set_language(lang_code: str):
    """Set the application language"""
    get_localization().set_language(lang_code)


def get_language() -> str:
    """Get the current language code"""
    return get_localization().get_language()
