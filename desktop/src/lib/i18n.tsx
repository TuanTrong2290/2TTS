import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { ipcClient } from './ipc';

// Default English translations (fallback)
const DEFAULT_TRANSLATIONS: Record<string, string> = {
  // Navigation
  'nav.tts': 'Text to Speech',
  'nav.transcribe': 'Transcribe',
  'nav.settings': 'Settings',
  
  // Common
  'common.start': 'Start',
  'common.stop': 'Stop',
  'common.pause': 'Pause',
  'common.resume': 'Resume',
  'common.save': 'Save',
  'common.cancel': 'Cancel',
  'common.close': 'Close',
  'common.clear': 'Clear',
  'common.delete': 'Delete',
  'common.add': 'Add',
  'common.remove': 'Remove',
  'common.refresh': 'Refresh',
  'common.search': 'Search',
  'common.apply': 'Apply',
  'common.browse': 'Browse',
  'common.characters': 'characters',
  'common.lines': 'lines',
  'common.loading': 'Loading...',
  'common.error': 'Error',
  'common.success': 'Success',
  'common.warning': 'Warning',
  'common.enable': 'Enable',
  'common.result': 'Result',
  'common.export': 'Export',
  'common.copy': 'Copy',
  
  // TTS Page
  'tts.title': 'Text to Speech',
  'tts.drop_files': 'Drop files here or click to browse',
  'tts.supported_formats': 'Supported: TXT, SRT, DOCX',
  'tts.output_folder': 'Output Folder',
  'tts.select_folder': 'Select folder...',
  'tts.voice': 'Voice',
  'tts.select_voice': 'Select voice...',
  'tts.voice_library': 'Voice Library',
  'tts.credits': 'Credits',
  'tts.logs': 'Logs',
  'tts.debug': 'Debug',
  'tts.join_mp3': 'Join MP3',
  'tts.generate_srt': 'Generate SRT',
  'tts.no_lines': 'No lines yet',
  'tts.import_files': 'Import text files to get started',
  'tts.processing': 'Processing...',
  'tts.completed': 'Completed',
  'tts.failed': 'Failed',
  'tts.pending': 'Pending',
  
  // Voice Settings
  'voice.settings': 'Voice Settings',
  'voice.model': 'Model',
  'voice.stability': 'Stability',
  'voice.similarity': 'Similarity',
  'voice.style': 'Style Exaggeration',
  'voice.speed': 'Speed',
  'voice.speaker_boost': 'Speaker Boost',
  'voice.auto_pauses': 'Auto Pauses',
  'voice.short_pause': 'Short pause (ms)',
  'voice.long_pause': 'Long pause (ms)',
  'voice.v3_tip': 'V3 Audio Tags: Add emotion with tags like [laughs], [whispers], [sarcastic] in your text.',
  
  // Table columns
  'table.index': '#',
  'table.text': 'Text',
  'table.voice': 'Voice',
  'table.status': 'Status',
  'table.duration': 'Duration',
  'table.selected': 'selected',
  'table.retry_selected': 'Retry Selected',
  'table.delete_selected': 'Delete Selected',
  'table.select_voice': 'Select voice...',
  
  // Status
  'status.pending': 'Pending',
  'status.processing': 'Processing',
  'status.done': 'Done',
  'status.error': 'Error',
  'status.ready': 'Ready',
  
  // Transcribe Page
  'transcribe.title': 'Transcribe',
  'transcribe.drop_media': 'Drop audio/video files here',
  'transcribe.supported_media': 'MP3, WAV, M4A, MP4, MKV, etc.',
  'transcribe.language': 'Language',
  'transcribe.auto_detect': 'Auto-detect',
  'transcribe.identify_speakers': 'Identify Speakers',
  'transcribe.num_speakers': 'Number of Speakers',
  'transcribe.start': 'Start Transcription',
  'transcribe.result': 'Result',
  'transcribe.copy': 'Copy',
  'transcribe.export': 'Export',
  
  // Settings Page
  'settings.title': 'Settings',
  'settings.general': 'General',
  'settings.processing': 'Processing',
  'settings.api_keys': 'API Keys',
  'settings.proxies': 'Proxies',
  'settings.presets': 'Presets',
  'settings.voice_patterns': 'Voice Patterns',
  'settings.analytics': 'Analytics',
  'settings.appearance': 'Appearance',
  'settings.language': 'Language',
  'settings.theme': 'Theme',
  'settings.dark': 'Dark',
  'settings.light': 'Light',
  'settings.theme_default': 'Default Dark',
  'settings.theme_light': 'Light',
  'settings.theme_midnight': 'Midnight Purple',
  'settings.theme_forest': 'Forest Green',
  'settings.background_image': 'Background Image',
  'settings.background_opacity': 'Opacity',
  'settings.background_blur': 'Blur',
  'settings.browse_image': 'Browse Image',
  'settings.clear_image': 'Clear Image',
  'settings.thread_count': 'Thread Count',
  'settings.max_retries': 'Max Retries',
  'settings.low_credit_threshold': 'Low Credit Threshold',
  'settings.export_diagnostics': 'Export Diagnostics',
  'settings.about': 'About',
  'settings.output_folder': 'Default Output Folder',
  'settings.save_changes': 'Save Changes',
  'settings.thread_count_desc': 'Parallel TTS processes',
  'settings.max_retries_desc': 'On API failure',
  'settings.language_desc': 'UI language',
  
  // API Keys
  'apikeys.title': 'API Keys',
  'apikeys.add': 'Add API Key',
  'apikeys.name': 'Name',
  'apikeys.key': 'API Key',
  'apikeys.credits': 'Credits',
  'apikeys.validate': 'Validate',
  'apikeys.remove': 'Remove',
  'apikeys.status': 'API Key Status',
  'apikeys.total': 'Total',
  'apikeys.active': 'Currently Active',
  'apikeys.no_active': 'No active API key available',
  'apikeys.exhausted': 'Exhausted Keys',
  'apikeys.configured': 'configured',
  'apikeys.validate_all': 'Validate All',
  'apikeys.validating': 'Validating',
  'apikeys.valid': 'Valid',
  'apikeys.invalid': 'Invalid',
  'apikeys.add_placeholder': 'Enter API key...',
  'apikeys.loading': 'Loading API keys...',
  'apikeys.no_keys': 'No API keys configured. Add one below.',
  
  // Proxies
  'proxies.title': 'Proxies',
  'proxies.add': 'Add Proxy',
  'proxies.name': 'Proxy name',
  'proxies.host': 'Host',
  'proxies.port': 'Port',
  'proxies.type': 'Type',
  'proxies.test': 'Test',
  'proxies.healthy': 'Healthy',
  'proxies.unhealthy': 'Unhealthy',
  'proxies.no_proxies': 'No proxies configured.',
  'proxies.guide_title': 'How to Use Proxies',
  'proxies.guide_what': 'What are proxies?',
  'proxies.guide_what_desc': 'Proxies route your API requests through an intermediate server, useful for bypassing network restrictions or distributing requests.',
  'proxies.guide_steps': 'Quick Setup:',
  'proxies.guide_step1': 'Enter a name to identify this proxy',
  'proxies.guide_step2': 'Enter the proxy host (e.g., proxy.example.com or 192.168.1.100)',
  'proxies.guide_step3': 'Set the port number (common: 8080, 3128, 1080 for SOCKS5)',
  'proxies.guide_step4': 'Select proxy type: HTTP for most cases, SOCKS5 for advanced routing',
  'proxies.guide_step5': 'Click "Test" to verify the proxy works with ElevenLabs API',
  'proxies.guide_tip': 'Tip: Proxies are automatically used when assigned to API keys. A green status means the proxy can reach ElevenLabs servers.',
  'proxies.show_guide': 'Show setup guide',
  'proxies.dismiss_guide': 'Dismiss',
  'proxies.add_new': 'Add New Proxy',
  'proxies.name_placeholder': 'My Proxy',
  'proxies.name_hint': 'Friendly name to identify this proxy',
  'proxies.host_placeholder': 'proxy.example.com',
  'proxies.host_hint': 'Hostname or IP address',
  'proxies.port_hint': 'Common: 8080, 3128, 1080',
  'proxies.type_hint': 'HTTP works for most cases',
  'proxies.type_http_desc': 'Standard web proxy',
  'proxies.type_https_desc': 'Encrypted proxy',
  'proxies.type_socks5_desc': 'Advanced routing',
  'proxies.auth_toggle': 'Authentication (optional)',
  'proxies.username_placeholder': 'Username',
  'proxies.password_placeholder': 'Password',
  'proxies.auth_hint': 'Only required if your proxy requires authentication',
  'proxies.add_button': 'Add Proxy',
  'proxies.test_tooltip': 'Test connection to ElevenLabs API through this proxy',
  'proxies.remove_tooltip': 'Remove this proxy',
  'proxies.manual_mode': 'Manual',
  'proxies.import_mode': 'Quick Import',
  'proxies.import_placeholder': 'Paste proxy strings (one per line):\nhost:port\nhost:port:user:pass\nuser:pass@host:port\nsocks5://host:port',
  'proxies.import_formats': 'Supported formats: host:port, host:port:user:pass, user:pass@host:port, protocol://...',
  'proxies.import_button': 'Import Proxies',
  'proxies.import_empty': 'No proxy strings to import',
  'proxies.import_result': 'Imported',
  'proxies.import_success': 'success',
  'proxies.import_failed': 'failed',
  
  // Update Dialog
  'update.available': 'Update Available',
  'update.current': 'Current Version',
  'update.new': 'New Version',
  'update.download': 'Download & Install',
  'update.later': 'Later',
  
  // About
  'about.description': 'Text-to-Speech Tool',
  'about.ui_version': 'UI Version',
  'about.backend_version': 'Backend Version',
  'about.check_updates': 'Check for Updates',
  
  // Common extras
  'common.unknown': 'Unknown',
};

// Vietnamese translations
const VI_TRANSLATIONS: Record<string, string> = {
  // Navigation
  'nav.tts': 'Chuyển văn bản',
  'nav.transcribe': 'Chuyển giọng nói',
  'nav.settings': 'Cài đặt',
  
  // Common
  'common.start': 'Bắt đầu',
  'common.stop': 'Dừng',
  'common.pause': 'Tạm dừng',
  'common.resume': 'Tiếp tục',
  'common.save': 'Lưu',
  'common.cancel': 'Hủy',
  'common.close': 'Đóng',
  'common.clear': 'Xóa',
  'common.delete': 'Xóa',
  'common.add': 'Thêm',
  'common.remove': 'Xóa',
  'common.refresh': 'Làm mới',
  'common.search': 'Tìm kiếm',
  'common.apply': 'Áp dụng',
  'common.browse': 'Duyệt',
  'common.characters': 'ký tự',
  'common.lines': 'dòng',
  'common.loading': 'Đang tải...',
  'common.error': 'Lỗi',
  'common.success': 'Thành công',
  'common.warning': 'Cảnh báo',
  'common.enable': 'Bật',
  'common.result': 'Kết quả',
  'common.export': 'Xuất',
  'common.copy': 'Sao chép',
  
  // TTS Page
  'tts.title': 'Chuyển văn bản thành giọng nói',
  'tts.drop_files': 'Kéo thả tệp vào đây hoặc nhấp để duyệt',
  'tts.supported_formats': 'Hỗ trợ: TXT, SRT, DOCX',
  'tts.output_folder': 'Thư mục xuất',
  'tts.select_folder': 'Chọn thư mục...',
  'tts.voice': 'Giọng nói',
  'tts.select_voice': 'Chọn giọng nói...',
  'tts.voice_library': 'Thư viện giọng',
  'tts.credits': 'Tín dụng',
  'tts.logs': 'Nhật ký',
  'tts.debug': 'Gỡ lỗi',
  'tts.join_mp3': 'Ghép MP3',
  'tts.generate_srt': 'Tạo SRT',
  'tts.no_lines': 'Chưa có dòng nào',
  'tts.import_files': 'Nhập tệp văn bản để bắt đầu',
  'tts.processing': 'Đang xử lý...',
  'tts.completed': 'Hoàn thành',
  'tts.failed': 'Thất bại',
  'tts.pending': 'Chờ xử lý',
  
  // Voice Settings
  'voice.settings': 'Cài đặt giọng nói',
  'voice.model': 'Mô hình',
  'voice.stability': 'Độ ổn định',
  'voice.similarity': 'Độ tương đồng',
  'voice.style': 'Phong cách',
  'voice.speed': 'Tốc độ',
  'voice.speaker_boost': 'Tăng cường giọng',
  'voice.auto_pauses': 'Tự động ngắt',
  'voice.short_pause': 'Ngắt ngắn (ms)',
  'voice.long_pause': 'Ngắt dài (ms)',
  'voice.v3_tip': 'Thẻ V3: Thêm cảm xúc với [laughs], [whispers], [sarcastic] trong văn bản.',
  
  // Table columns
  'table.index': 'STT',
  'table.text': 'Văn bản',
  'table.voice': 'Giọng',
  'table.status': 'Trạng thái',
  'table.duration': 'Thời lượng',
  'table.selected': 'đã chọn',
  'table.retry_selected': 'Thử lại',
  'table.delete_selected': 'Xóa đã chọn',
  'table.select_voice': 'Chọn giọng...',
  
  // Status
  'status.pending': 'Chờ xử lý',
  'status.processing': 'Đang xử lý',
  'status.done': 'Hoàn thành',
  'status.error': 'Lỗi',
  'status.ready': 'Sẵn sàng',
  
  // Transcribe Page
  'transcribe.title': 'Chuyển giọng nói thành văn bản',
  'transcribe.drop_media': 'Kéo thả tệp âm thanh/video vào đây',
  'transcribe.supported_media': 'MP3, WAV, M4A, MP4, MKV, v.v.',
  'transcribe.language': 'Ngôn ngữ',
  'transcribe.auto_detect': 'Tự động nhận diện',
  'transcribe.identify_speakers': 'Nhận diện người nói',
  'transcribe.num_speakers': 'Số người nói',
  'transcribe.start': 'Bắt đầu chuyển đổi',
  'transcribe.result': 'Kết quả',
  'transcribe.copy': 'Sao chép',
  'transcribe.export': 'Xuất',
  
  // Settings Page
  'settings.title': 'Cài đặt',
  'settings.general': 'Chung',
  'settings.processing': 'Xử lý',
  'settings.api_keys': 'API Keys',
  'settings.proxies': 'Proxy',
  'settings.presets': 'Preset',
  'settings.voice_patterns': 'Mẫu giọng',
  'settings.analytics': 'Thống kê',
  'settings.appearance': 'Giao diện',
  'settings.language': 'Ngôn ngữ',
  'settings.theme': 'Giao diện',
  'settings.dark': 'Tối',
  'settings.light': 'Sáng',
  'settings.theme_default': 'Tối Mặc định',
  'settings.theme_light': 'Sáng',
  'settings.theme_midnight': 'Tím Huyền bí',
  'settings.theme_forest': 'Xanh Rừng thẳm',
  'settings.background_image': 'Hình nền',
  'settings.background_opacity': 'Độ trong suốt',
  'settings.background_blur': 'Độ làm mờ',
  'settings.browse_image': 'Chọn ảnh',
  'settings.clear_image': 'Xóa ảnh',
  'settings.thread_count': 'Số luồng',
  'settings.max_retries': 'Số lần thử lại',
  'settings.low_credit_threshold': 'Ngưỡng tín dụng thấp',
  'settings.export_diagnostics': 'Xuất chẩn đoán',
  'settings.about': 'Giới thiệu',
  'settings.output_folder': 'Thư mục xuất mặc định',
  'settings.save_changes': 'Lưu thay đổi',
  'settings.thread_count_desc': 'Số tiến trình TTS song song',
  'settings.max_retries_desc': 'Khi API lỗi',
  'settings.language_desc': 'Ngôn ngữ giao diện',
  
  // API Keys
  'apikeys.title': 'Quản lý API Key',
  'apikeys.add': 'Thêm API Key',
  'apikeys.name': 'Tên',
  'apikeys.key': 'API Key',
  'apikeys.credits': 'Tín dụng',
  'apikeys.validate': 'Xác thực',
  'apikeys.remove': 'Xóa',
  'apikeys.status': 'Trạng thái API Key',
  'apikeys.total': 'Tổng',
  'apikeys.active': 'Đang hoạt động',
  'apikeys.no_active': 'Không có API key khả dụng',
  'apikeys.exhausted': 'Key đã hết hạn',
  'apikeys.configured': 'đã cấu hình',
  'apikeys.validate_all': 'Xác thực tất cả',
  'apikeys.validating': 'Đang xác thực',
  'apikeys.valid': 'Hợp lệ',
  'apikeys.invalid': 'Không hợp lệ',
  'apikeys.add_placeholder': 'Nhập API key...',
  'apikeys.loading': 'Đang tải API keys...',
  'apikeys.no_keys': 'Chưa có API key. Thêm key bên dưới.',
  
  // Proxies
  'proxies.title': 'Quản lý Proxy',
  'proxies.add': 'Thêm Proxy',
  'proxies.name': 'Tên proxy',
  'proxies.host': 'Máy chủ',
  'proxies.port': 'Cổng',
  'proxies.type': 'Loại',
  'proxies.test': 'Kiểm tra',
  'proxies.healthy': 'Hoạt động',
  'proxies.unhealthy': 'Lỗi',
  'proxies.no_proxies': 'Chưa cấu hình proxy.',
  'proxies.guide_title': 'Hướng dẫn sử dụng Proxy',
  'proxies.guide_what': 'Proxy là gì?',
  'proxies.guide_what_desc': 'Proxy định tuyến yêu cầu API qua máy chủ trung gian, hữu ích để vượt qua giới hạn mạng hoặc phân tán yêu cầu.',
  'proxies.guide_steps': 'Thiết lập nhanh:',
  'proxies.guide_step1': 'Nhập tên để nhận diện proxy này',
  'proxies.guide_step2': 'Nhập địa chỉ proxy (VD: proxy.example.com hoặc 192.168.1.100)',
  'proxies.guide_step3': 'Đặt số cổng (phổ biến: 8080, 3128, 1080 cho SOCKS5)',
  'proxies.guide_step4': 'Chọn loại proxy: HTTP cho hầu hết trường hợp, SOCKS5 cho định tuyến nâng cao',
  'proxies.guide_step5': 'Nhấn "Kiểm tra" để xác nhận proxy hoạt động với ElevenLabs API',
  'proxies.guide_tip': 'Mẹo: Proxy tự động được sử dụng khi gán cho API key. Trạng thái xanh nghĩa là proxy có thể kết nối đến máy chủ ElevenLabs.',
  'proxies.show_guide': 'Hiện hướng dẫn',
  'proxies.dismiss_guide': 'Ẩn',
  'proxies.add_new': 'Thêm Proxy mới',
  'proxies.name_placeholder': 'Proxy của tôi',
  'proxies.name_hint': 'Tên thân thiện để nhận diện proxy',
  'proxies.host_placeholder': 'proxy.example.com',
  'proxies.host_hint': 'Tên máy chủ hoặc địa chỉ IP',
  'proxies.port_hint': 'Phổ biến: 8080, 3128, 1080',
  'proxies.type_hint': 'HTTP phù hợp cho hầu hết trường hợp',
  'proxies.type_http_desc': 'Proxy web tiêu chuẩn',
  'proxies.type_https_desc': 'Proxy mã hóa',
  'proxies.type_socks5_desc': 'Định tuyến nâng cao',
  'proxies.auth_toggle': 'Xác thực (tùy chọn)',
  'proxies.username_placeholder': 'Tên đăng nhập',
  'proxies.password_placeholder': 'Mật khẩu',
  'proxies.auth_hint': 'Chỉ cần thiết nếu proxy yêu cầu xác thực',
  'proxies.add_button': 'Thêm Proxy',
  'proxies.test_tooltip': 'Kiểm tra kết nối đến ElevenLabs API qua proxy này',
  'proxies.remove_tooltip': 'Xóa proxy này',
  'proxies.manual_mode': 'Thủ công',
  'proxies.import_mode': 'Nhập nhanh',
  'proxies.import_placeholder': 'Dán chuỗi proxy (mỗi dòng một proxy):\nhost:port\nhost:port:user:pass\nuser:pass@host:port\nsocks5://host:port',
  'proxies.import_formats': 'Định dạng hỗ trợ: host:port, host:port:user:pass, user:pass@host:port, protocol://...',
  'proxies.import_button': 'Nhập Proxy',
  'proxies.import_empty': 'Không có chuỗi proxy để nhập',
  'proxies.import_result': 'Đã nhập',
  'proxies.import_success': 'thành công',
  'proxies.import_failed': 'thất bại',
  
  // Update Dialog
  'update.available': 'Có bản cập nhật',
  'update.current': 'Phiên bản hiện tại',
  'update.new': 'Phiên bản mới',
  'update.download': 'Tải & Cài đặt',
  'update.later': 'Để sau',
  
  // About
  'about.description': 'Công cụ chuyển văn bản thành giọng nói',
  'about.ui_version': 'Phiên bản UI',
  'about.backend_version': 'Phiên bản Backend',
  'about.check_updates': 'Kiểm tra cập nhật',
  
  // Common extras
  'common.unknown': 'Không xác định',
};

const TRANSLATIONS: Record<string, Record<string, string>> = {
  en: DEFAULT_TRANSLATIONS,
  vi: VI_TRANSLATIONS,
};

interface I18nContextType {
  language: string;
  setLanguage: (lang: string) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextType | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState('en');
  const [translations, setTranslations] = useState<Record<string, string>>(DEFAULT_TRANSLATIONS);

  useEffect(() => {
    // Load saved language preference
    const savedLang = localStorage.getItem('app_language') || 'en';
    setLanguageState(savedLang);
    loadTranslations(savedLang);
  }, []);

  const loadTranslations = async (lang: string) => {
    // Use local translations
    const localTranslations = TRANSLATIONS[lang] || DEFAULT_TRANSLATIONS;
    setTranslations(localTranslations);
    
    // Optionally fetch from backend for additional translations
    try {
      const backendTranslations = await ipcClient.getTranslations(lang);
      // Merge with local translations (local takes precedence for UI keys)
      setTranslations({ ...backendTranslations, ...localTranslations });
    } catch {
      // Use local translations only
    }
  };

  const setLanguage = (lang: string) => {
    setLanguageState(lang);
    localStorage.setItem('app_language', lang);
    loadTranslations(lang);
    
    // Also save to backend config
    ipcClient.setConfig('app_language', lang).catch(() => {});
  };

  const t = (key: string, params?: Record<string, string | number>): string => {
    let text = translations[key] || DEFAULT_TRANSLATIONS[key] || key;
    
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        text = text.replace(`{${k}}`, String(v));
      });
    }
    
    return text;
  };

  return (
    <I18nContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useTranslation() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useTranslation must be used within I18nProvider');
  }
  return context;
}

export const AVAILABLE_LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'vi', name: 'Tiếng Việt' },
];
