import os

file_path = r'd:\DENTIX\frontend\src\locales\ar\translation.json'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read().strip()

# Remove last }
if content.endswith('}'):
    content = content[:-1].strip()
    
# Remove last } again for the outer object if it was matched
if content.endswith('}'):
    content = content[:-1].rstrip()

new_content = content + """,
    "command_palette": {
        "placeholder": "ابحث عن أي شيء...",
        "results_label": "نتائج البحث",
        "no_results": "لم يتم العثور على نتائج",
        "no_results_desc": "لم نتمكن من العثور على نتائج لـ "{{query}}"",
        "quick_nav": "انتقال سريع",
        "add_patient": "إضافة مريض",
        "new_appointment": "موعد جديد",
        "inventory_check": "فحص المخزون",
        "settings": "الإعدادات",
        "to_close": "للإغلاق",
        "to_select": "للاختيار",
        "go_to": "انتقال إلى",
        "sections": {
            "patients": "المرضى",
            "appointments": "المواعيد",
            "pages": "الصفحات",
            "actions": "الإجراءات"
        }
    }
}
}"""

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)
