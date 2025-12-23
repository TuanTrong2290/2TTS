// Simple language detection based on character patterns
// Returns ISO 639-1 language code

// Vietnamese-specific characters (with diacritics)
const VIETNAMESE_CHARS = /[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]/;

// Chinese characters (CJK)
const CHINESE_CHARS = /[\u4e00-\u9fff\u3400-\u4dbf]/;

// Japanese-specific (Hiragana, Katakana)
const JAPANESE_CHARS = /[\u3040-\u309f\u30a0-\u30ff]/;

// Korean (Hangul)
const KOREAN_CHARS = /[\uac00-\ud7af\u1100-\u11ff]/;

// Arabic
const ARABIC_CHARS = /[\u0600-\u06ff]/;

// Cyrillic (Russian, Ukrainian, etc.)
const CYRILLIC_CHARS = /[\u0400-\u04ff]/;

// Thai
const THAI_CHARS = /[\u0e00-\u0e7f]/;

// Hindi/Devanagari
const HINDI_CHARS = /[\u0900-\u097f]/;

export type DetectedLanguage = {
  code: string;
  name: string;
  confidence: 'high' | 'medium' | 'low';
};

export function detectLanguage(text: string): DetectedLanguage {
  if (!text || text.trim().length === 0) {
    return { code: 'en', name: 'English', confidence: 'low' };
  }

  // Count character matches
  const vietnameseCount = (text.match(VIETNAMESE_CHARS) || []).length;
  const chineseCount = (text.match(CHINESE_CHARS) || []).length;
  const japaneseCount = (text.match(JAPANESE_CHARS) || []).length;
  const koreanCount = (text.match(KOREAN_CHARS) || []).length;
  const arabicCount = (text.match(ARABIC_CHARS) || []).length;
  const cyrillicCount = (text.match(CYRILLIC_CHARS) || []).length;
  const thaiCount = (text.match(THAI_CHARS) || []).length;
  const hindiCount = (text.match(HINDI_CHARS) || []).length;

  const totalChars = text.replace(/\s/g, '').length;
  
  // Vietnamese detection (high priority due to unique diacritics)
  if (vietnameseCount > 0) {
    const ratio = vietnameseCount / totalChars;
    if (ratio > 0.1 || vietnameseCount >= 3) {
      return { code: 'vi', name: 'Vietnamese', confidence: ratio > 0.2 ? 'high' : 'medium' };
    }
  }

  // Chinese detection
  if (chineseCount > totalChars * 0.3) {
    // Check if also has Japanese characters (might be Japanese with Kanji)
    if (japaneseCount > 0) {
      return { code: 'ja', name: 'Japanese', confidence: 'high' };
    }
    return { code: 'zh', name: 'Chinese', confidence: 'high' };
  }

  // Japanese detection
  if (japaneseCount > 0) {
    return { code: 'ja', name: 'Japanese', confidence: 'high' };
  }

  // Korean detection
  if (koreanCount > totalChars * 0.2) {
    return { code: 'ko', name: 'Korean', confidence: 'high' };
  }

  // Arabic detection
  if (arabicCount > totalChars * 0.3) {
    return { code: 'ar', name: 'Arabic', confidence: 'high' };
  }

  // Cyrillic detection (Russian as default)
  if (cyrillicCount > totalChars * 0.3) {
    return { code: 'ru', name: 'Russian', confidence: 'medium' };
  }

  // Thai detection
  if (thaiCount > totalChars * 0.3) {
    return { code: 'th', name: 'Thai', confidence: 'high' };
  }

  // Hindi detection
  if (hindiCount > totalChars * 0.3) {
    return { code: 'hi', name: 'Hindi', confidence: 'high' };
  }

  // Default to English
  return { code: 'en', name: 'English', confidence: 'low' };
}

// Model language support mapping
export const MODEL_LANGUAGE_SUPPORT: Record<string, {
  languages: string[];
  allLanguages: boolean;
  name: string;
}> = {
  'eleven_v3': {
    name: 'Eleven V3',
    allLanguages: true, // 70+ languages
    languages: [], // Supports almost all
  },
  'eleven_multilingual_v2': {
    name: 'Multilingual V2',
    allLanguages: false,
    languages: ['en', 'ja', 'zh', 'de', 'hi', 'fr', 'ko', 'pt', 'it', 'es', 'id', 'nl', 'tr', 'fil', 'pl', 'sv', 'bg', 'ro', 'ar', 'cs', 'el', 'fi', 'hr', 'ms', 'sk', 'da', 'ta', 'uk', 'ru'],
  },
  'eleven_turbo_v2_5': {
    name: 'Turbo V2.5',
    allLanguages: false,
    languages: ['en', 'ja', 'zh', 'de', 'hi', 'fr', 'ko', 'pt', 'it', 'es', 'id', 'nl', 'tr', 'fil', 'pl', 'sv', 'bg', 'ro', 'ar', 'cs', 'el', 'fi', 'hr', 'ms', 'sk', 'da', 'ta', 'uk', 'ru', 'hu', 'no', 'vi'],
  },
  'eleven_turbo_v2': {
    name: 'Turbo V2',
    allLanguages: false,
    languages: ['en'],
  },
  'eleven_flash_v2_5': {
    name: 'Flash V2.5',
    allLanguages: false,
    languages: ['en', 'ja', 'zh', 'de', 'hi', 'fr', 'ko', 'pt', 'it', 'es', 'id', 'nl', 'tr', 'fil', 'pl', 'sv', 'bg', 'ro', 'ar', 'cs', 'el', 'fi', 'hr', 'ms', 'sk', 'da', 'ta', 'uk', 'ru', 'hu', 'no', 'vi'],
  },
  'eleven_flash_v2': {
    name: 'Flash V2',
    allLanguages: false,
    languages: ['en'],
  },
};

export function isLanguageSupported(modelId: string, languageCode: string): boolean {
  const model = MODEL_LANGUAGE_SUPPORT[modelId];
  if (!model) return true; // Unknown model, assume supported
  if (model.allLanguages) return true;
  return model.languages.includes(languageCode);
}

export function getSupportedModelsForLanguage(languageCode: string): string[] {
  return Object.entries(MODEL_LANGUAGE_SUPPORT)
    .filter(([_, model]) => model.allLanguages || model.languages.includes(languageCode))
    .map(([id]) => id);
}

export function getBestModelForLanguage(languageCode: string): string {
  // Priority: V3 > Turbo V2.5 > Flash V2.5 > Multilingual V2
  const supportedModels = getSupportedModelsForLanguage(languageCode);
  
  const priority = [
    'eleven_v3',
    'eleven_turbo_v2_5', 
    'eleven_flash_v2_5',
    'eleven_multilingual_v2',
    'eleven_turbo_v2',
    'eleven_flash_v2',
  ];
  
  for (const model of priority) {
    if (supportedModels.includes(model)) {
      return model;
    }
  }
  
  return 'eleven_v3'; // Fallback
}
