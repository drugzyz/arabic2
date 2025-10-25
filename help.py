# [file name]: help.py
# -*- coding: utf-8 -*-

import textwrap

# تعريف المتغيرات العالمية
send_msg = None
get_user_permission_level = None
plugin_system = None

def init_plugin(global_vars):
    """تهيئة البلجن بالمتغيرات العالمية"""
    global send_msg, get_user_permission_level, plugin_system
    
    # استيراد الدوال من النظام الرئيسي
    send_msg = global_vars.get('send_msg')
    get_user_permission_level = global_vars.get('get_user_permission_level')
    
    # استيراد نظام البلاجنات
    from system import plugin_system as ps
    plugin_system = ps
    
    print("✅ تم تهيئة بلجن المساعدة")

def organize_commands_by_level(jid, nick, room):
    """تنظيم الأوامر حسب مستوى الصلاحية"""
    user_level = get_user_permission_level(jid, nick, room)
    
    # تصنيف الأوامر حسب المستوى
    commands_by_level = {
        "المستخدم العادي (المستوى 1-4)": [],
        "العضو المميز (المستوى 5)": [],
        "المدير (المستوى 6)": [],
        "المشرف (المستوى 7)": [],
        "مالك الغرفة (المستوى 8)": [],
        "المطور (المستوى 9)": [],
        "مالك البوت (المستوى 10)": []
    }
    
    # جمع الأوامر من جميع البلاجنات
    all_commands = []
    for cmd in plugin_system.commands:
        level, cmd_name, func, min_args, help_text = cmd
        if user_level >= level:  # عرض الأوامر التي يمكن للمستخدم استخدامها فقط
            all_commands.append(cmd)
    
    # تنظيم الأوامر حسب المستوى
    for cmd in all_commands:
        level, cmd_name, func, min_args, help_text = cmd
        
        if level <= 4:
            category = "المستخدم العادي (المستوى 1-4)"
        elif level == 5:
            category = "العضو المميز (المستوى 5)"
        elif level == 6:
            category = "المدير (المستوى 6)"
        elif level == 7:
            category = "المشرف (المستوى 7)"
        elif level == 8:
            category = "مالك الغرفة (المستوى 8)"
        elif level == 9:
            category = "المطور (المستوى 9)"
        else:
            category = "مالك البوت (المستوى 10)"
        
        commands_by_level[category].append((cmd_name, help_text, min_args))
    
    return commands_by_level, user_level

def format_command_list(commands_dict, user_level):
    """تنسيق قائمة الأوامر بشكل منظم"""
    message_parts = []
    
    message_parts.append("🤖 **قائمة أوامر البوت**")
    message_parts.append(f"📊 **مستوى صلاحيتك الحالي: {user_level}**")
    message_parts.append("=" * 50)
    
    for category, commands in commands_dict.items():
        if commands:  # عرض الفئات التي تحتوي على أوامر فقط
            message_parts.append(f"\n🎯 **{category}**:")
            message_parts.append("-" * 30)
            
            # ترتيب الأوامر أبجديًا
            commands.sort(key=lambda x: x[0])
            
            for cmd_name, help_text, min_args in commands:
                # تنسيق المساعدة لتناسب العرض
                formatted_help = help_text
                if len(formatted_help) > 60:
                    formatted_help = formatted_help[:57] + "..."
                
                message_parts.append(f"• `!{cmd_name}` - {formatted_help}")
    
    # إضافة نصائح استخدام
    message_parts.append("\n💡 **نصائح الاستخدام:**")
    message_parts.append("• اكتب `!مساعدة [اسم الأمر]` للحصول على شرح مفصل")
    message_parts.append("• الأرقام في نهاية الأوامر تدل على عدد الوسائط المطلوبة")
    message_parts.append("• استخدم `!فحص` لمعرفة صلاحياتك الحالية")
    
    return "\n".join(message_parts)

def get_command_detail(command_name, jid, nick, room):
    """الحصول على تفاصيل أمر معين"""
    user_level = get_user_permission_level(jid, nick, room)
    
    for cmd in plugin_system.commands:
        level, cmd_name, func, min_args, help_text = cmd
        if cmd_name == command_name:
            if user_level >= level:
                # بناء رسالة تفصيلية
                detail_message = [
                    f"🔍 **تفاصيل الأمر: `!{command_name}`**",
                    "=" * 40,
                    f"📝 **الوصف:** {help_text}",
                    f"📊 **مستوى الصلاحية المطلوب:** {level}",
                    f"🔢 **عدد الوسائط المطلوبة:** {min_args}",
                    f"✅ **صلاحيتك الحالية:** {user_level} - {'🟢 مسموح' if user_level >= level else '🔴 ممنوع'}"
                ]
                
                # إضافة أمثلة استخدام بناءً على نوع الأمر
                examples = get_command_examples(command_name)
                if examples:
                    detail_message.append(f"\n💡 **أمثلة الاستخدام:**")
                    for example in examples:
                        detail_message.append(f"• `{example}`")
                
                # إضافة نصائح لاستخدام خاطئ
                common_mistakes = get_common_mistakes(command_name)
                if common_mistakes:
                    detail_message.append(f"\n⚠️ **الأخطاء الشائعة:**")
                    for mistake in common_mistakes:
                        detail_message.append(f"• {mistake}")
                
                return "\n".join(detail_message)
            else:
                return f"❌ **لا تملك الصلاحية الكافية لاستخدام `!{command_name}`**\nمستوى الصلاحية المطلوب: {level} - مستواك الحالي: {user_level}"
    
    return f"❌ **الأمر `!{command_name}` غير معروف**\nاكتب `!مساعدة` لرؤية الأوامر المتاحة"

def get_command_examples(command_name):
    """إرجاع أمثلة استخدام للأمر"""
    examples = {
        'ذكاء': [
            '!ذكاء ما هي عاصمة فرنسا؟',
            '!ذكاء اشرح نظرية النسبية',
            '!ذكاء كيف يمكنني تعلم البرمجة؟'
        ],
        'تلخيص': [
            '!تلخيص نص طويل عن التكنولوجيا...',
            '!تلخيص مقال عن الذكاء الاصطناعي'
        ],
        'ترجمة': [
            '!ترجمة مرحبا إلى الإنجليزية',
            '!ترجمة Hello world إلى العربية',
            '!ترجمة كيف حالك إلى الفرنسية'
        ],
        'كود': [
            '!كود دالة بايثون لحساب مجموع الأعداد',
            '!كود صفحة HTML مع CSS',
            '!كود كائن جافاسكريبت لإدارة المستخدمين'
        ],
        'طرد': [
            '!طرد اسم_المستخدم',
            '!طرد john'
        ],
        'حظر': [
            '!حظر user@example.com',
            '!حظر spammer@domain.com'
        ],
        'كتم': [
            '!كتم اسم_المستخدم',
            '!كتم john'
        ],
        'قول': [
            '!قول مرحبا بالجميع',
            '!قول هذا نص تجريبي'
        ],
        'موضوع': [
            '!موضوع مناقشة عامة',
            '!موضوع غرفة الدردشة الرئيسية'
        ],
        'فحص': [
            '!فحص',
            '!فحص معلومات'
        ],
        'قفل_الخاص': [
            '!قفل_الخاص',
            '!خاص'
        ]
    }
    
    return examples.get(command_name, [])

def get_common_mistakes(command_name):
    """إرجاع الأخطاء الشائعة في استخدام الأمر"""
    mistakes = {
        'ذكاء': [
            'نسيان كتابة السؤال بعد الأمر',
            'استخدام رموز غير مدعومة في السؤال'
        ],
        'ترجمة': [
            'نسيان كلمة "إلى" بين النص واللغة',
            'عدم تحديد اللغة المستهدفة',
            'استخدام رموز غير مدعومة في النص'
        ],
        'كود': [
            'عدم تقديم وصف كافٍ للكود المطلوب',
            'طلب كود بلغة غير مدعومة'
        ],
        'طرد': [
            'طرد مستخدم غير موجود',
            'محاولة طرد مشرف أو مالك'
        ],
        'حظر': [
            'حظر بدون JID صالح',
            'نسيان @ في JID'
        ],
        'كتم': [
            'كتم مستخدم غير موجود',
            'محاولة كتم مشرف أو مالك'
        ]
    }
    
    return mistakes.get(command_name, [])

def format_incorrect_usage(command_name, correct_usage):
    """تنسيق رسالة الاستخدام الخاطئ"""
    return [
        f"⚠️ **استخدام خاطئ للأمر `!{command_name}`**",
        "=" * 40,
        f"📝 **الاستخدام الصحيح:** `{correct_usage}`",
        f"💡 **لمزيد من المساعدة:** اكتب `!مساعدة {command_name}`"
    ]

def handle_incorrect_usage(msg_type, jid, nick, command_name, user_input=""):
    """معالجة الاستخدام الخاطئ للأمر"""
    usage_guides = {
        'ذكاء': "!ذكاء [سؤال أو نص]",
        'تلخيص': "!تلخيص [النص الطويل]",
        'ترجمة': "!ترجمة [النص] إلى [اللغة]",
        'كود': "!كود [وصف الكود المطلوب]",
        'طرد': "!طرد [اسم المستخدم]",
        'حظر': "!حظر [JID المستخدم]",
        'كتم': "!كتم [اسم المستخدم]",
        'قول': "!قول [النص]",
        'موضوع': "!موضوع [النص]",
        'فحص': "!فحص",
        'قفل_الخاص': "!قفل_الخاص"
    }
    
    correct_usage = usage_guides.get(command_name, f"!{command_name} [وسائط]")
    message_lines = format_incorrect_usage(command_name, correct_usage)
    
    # إضافة أمثلة إذا كانت متاحة
    examples = get_command_examples(command_name)
    if examples:
        message_lines.append(f"\n💡 **أمثلة:**")
        for example in examples[:2]:  # عرض مثالين فقط
            message_lines.append(f"`{example}`")
    
    # إضافة تحليل للخطأ إذا كان هناك مدخلات
    if user_input:
        analysis = analyze_user_error(command_name, user_input)
        if analysis:
            message_lines.append(f"\n🔍 **تحليل الخطأ:** {analysis}")
    
    send_msg(msg_type, jid, nick, "\n".join(message_lines))

def analyze_user_error(command_name, user_input):
    """تحليل خطأ المستخدم وإرجاع نص مساعد"""
    analysis = {
        'ترجمة': lambda inp: "تأكد من استخدام صيغة 'النص إلى اللغة'" if 'إلى' not in inp else "تأكد من كتابة اللغة المستهدفة بشكل صحيح",
        'كود': lambda inp: "يرجى تقديم وصف أكثر تفصيلاً للكود المطلوب" if len(inp) < 10 else "الوصف جيد ولكن قد يحتاج لمزيد من التفاصيل",
        'حظر': lambda inp: "تأكد من كتابة JID كامل مع @" if '@' not in inp else "JID صحيح الشكل",
        'طرد': lambda inp: "تأكد من أن اسم المستخدم مكتوب بشكل صحيح" if not inp.strip() else "اسم المستخدم مكتوب"
    }
    
    analyzer = analysis.get(command_name)
    return analyzer(user_input) if analyzer else None

def مساعدة(msg_type, jid, nick, text):
    """عرض قائمة الأوامر أو مساعدة لأمر معين"""
    try:
        room = jid.split('/')[0] if '/' in jid else jid
        
        if not text.strip():
            # عرض جميع الأوامر
            commands_dict, user_level = organize_commands_by_level(jid, nick, room)
            help_message = format_command_list(commands_dict, user_level)
            
            # تقسيم الرسالة إذا كانت طويلة
            if len(help_message) > 1500:
                parts = split_long_message(help_message)
                for i, part in enumerate(parts, 1):
                    if i == 1:
                        send_msg(msg_type, jid, nick, part)
                    else:
                        send_msg(msg_type, jid, nick, f"📖 (تابع {i}):\n{part}")
                    # تأخير بسيط بين الأجزاء
                    import time
                    time.sleep(0.5)
            else:
                send_msg(msg_type, jid, nick, help_message)
                
        else:
            # عرض مساعدة لأمر معين
            command_name = text.strip().lower()
            detail_message = get_command_detail(command_name, jid, nick, room)
            send_msg(msg_type, jid, nick, detail_message)
            
    except Exception as e:
        error_msg = f"❌ خطأ في عرض المساعدة: {str(e)}"
        send_msg(msg_type, jid, nick, error_msg)

def split_long_message(message, max_length=1500):
    """تقسيم الرسالة الطويلة إلى أجزاء"""
    lines = message.split('\n')
    parts = []
    current_part = []
    current_length = 0
    
    for line in lines:
        if current_length + len(line) + 1 > max_length and current_part:
            parts.append('\n'.join(current_part))
            current_part = [line]
            current_length = len(line)
        else:
            current_part.append(line)
            current_length += len(line) + 1
    
    if current_part:
        parts.append('\n'.join(current_part))
    
    return parts

def تصحيح_الاستخدام(msg_type, jid, nick, text):
    """مساعدة تفصيلية لاستخدام أمر معين بشكل خاطئ"""
    if not text.strip():
        send_msg(msg_type, jid, nick, "⚠️ يرجى تحديد الأمر الذي تريد تصحيح استخدامه: !تصحيح_الاستخدام [اسم الأمر]")
        return
    
    parts = text.strip().split(' ', 1)
    command_name = parts[0].lower()
    user_input = parts[1] if len(parts) > 1 else ""
    
    handle_incorrect_usage(msg_type, jid, nick, command_name, user_input)

def execute():
    """الدالة الرئيسية لتحميل الأوامر"""
    
    commands = [
        (1, 'مساعدة', مساعدة, 0, 'عرض قائمة الأوامر أو مساعدة لأمر معين - !مساعدة [اسم الأمر]'),
        (1, 'مساعدة_تفصيلية', مساعدة, 0, 'مرادف لـ !مساعدة - !مساعدة_تفصيلية [اسم الأمر]'),
        (1, 'الاوامر', مساعدة, 0, 'عرض قائمة الأوامر - !الاوامر'),
        (1, 'تصحيح_الاستخدام', تصحيح_الاستخدام, 1, 'تصحيح استخدام أمر معين - !تصحيح_الاستخدام [اسم الأمر] [المدخلات]'),
        (1, 'help', مساعدة, 0, 'English help - !help [command name]'),
    ]
    
    print("✅ تم تحميل بلجن المساعدة المحسن مع نظام التصحيح التلقائي")
    return commands

# معالجات الأحداث
presence_control = []
message_act_control = []
iq_control = []
timer_functions = []