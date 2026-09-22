"""التحقق من صحة الحقول المستخرجة"""
from datetime import datetime


def validate_fields(fields):
    """التحقق من صحة الحقول"""
    errors = []
    warnings = []

    if fields.get('nin'):
        if len(fields['nin']) != 18:
            errors.append(f"NIN يجب أن يكون 18 رقم، وجد {len(fields['nin'])}")
    else:
        warnings.append("لم يتم استخراج NIN")

    if fields.get('birth_date'):
        try:
            birth = datetime.strptime(fields['birth_date'], '%Y-%m-%d')
            if birth > datetime.now():
                errors.append("تاريخ الميلاد في المستقبل!")
        except Exception:
            errors.append(f"تاريخ ميلاد غير صالح: {fields['birth_date']}")

    if fields.get('gender') and fields['gender'] not in ['M', 'F']:
        errors.append(f"جنس غير صالح: {fields['gender']}")

    return errors, warnings