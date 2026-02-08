import re

class ArabicNormalizer:
    """
    Utility for normalizing Arabic text to improve matching accuracy.
    """
    
    @staticmethod
    def normalize(text: str) -> str:
        if not text:
            return ""
            
        # 1. Normalize Alef (أ، إ، آ -> ا)
        text = re.sub("[أإآ]", "ا", text)
        
        # 2. Normalize Teh Marbuta (ة -> ه)
        # Note: In Egyptian dialect, ة is often written as ه, and vice versa.
        # We normalize to 'ه' to catch both.
        text = re.sub("ة", "ه", text)
        
        # 3. Normalize Yeh (ى -> ي)
        text = re.sub("ى", "ي", text)
        
        # 4. Remove Diacritics (Tashkeel)
        text = re.sub("[\u064B-\u065F]", "", text)
        
        return text.strip()

# Singleton
normalizer = ArabicNormalizer()
