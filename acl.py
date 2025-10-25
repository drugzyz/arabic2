# [file name]: acl.py
# -*- coding: utf-8 -*-

import xmpp
import time
import random
import re
import json
import operator
from datetime import datetime

# تعريف المتغيرات العامة
acl_acts = ['msg', 'prs', 'prs_change', 'prs_join', 'role', 'role_change', 'role_join', 'aff', 'aff_change', 'aff_join',
            'nick', 'nick_change', 'nick_join', 'all', 'all_change', 'all_join', 'jid', 'jidfull', 'res', 'age', 'ver', 'vcard']
acl_actions = ['show', 'del', 'clear'] + acl_acts
acl_actions.sort()

acl_ver_tmp = {}
acl_vcard_tmp = {}

def safe_decode(text):
    """فك ترميز النص بأمان"""
    if text is None:
        return ""
    
    if isinstance(text, str):
        return text
    
    if isinstance(text, bytes):
        try:
            return text.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return text.decode('utf-8', errors='ignore')
            except:
                return str(text, errors='ignore')
    
    return str(text)

def rand10():
    """إنشاء رقم عشوائي مكون من 10 أرقام"""
    return str(random.randint(1000000000, 9999999999))

def extract_room_from_jid(jid):
    """استخراج اسم الغرفة من JID"""
    if not jid:
        return ''
    if '/' in jid:
        return jid.split('/')[0]
    return jid

def get_client():
    """الحصول على عميل XMPP"""
    from run import client
    return client

def send_msg(ttype, jid, nick, text):
    """إرسال رسالة"""
    from run import send_msg as global_send_msg
    global_send_msg(ttype, jid, nick, text)

def get_user_permission_level(jid, nick, room):
    """الحصول على مستوى صلاحية المستخدم"""
    from run import get_user_permission_level as global_get_level
    return global_get_level(jid, nick, room)

def is_owner(jid):
    """التحقق إذا كان المستخدم مالكاً"""
    from run import is_owner as global_is_owner
    return global_is_owner(jid)

def db_execute(query, params=()):
    """تنفيذ استعلام قاعدة البيانات"""
    from run import db_execute as global_db_execute
    return global_db_execute(query, params)

def db_fetchall(query, params=()):
    """جلب جميع النتائج من قاعدة البيانات"""
    from run import db_fetchall as global_db_fetchall
    return global_db_fetchall(query, params)

def db_fetchone(query, params=()):
    """جلب نتيجة واحدة من قاعدة البيانات"""
    from run import db_fetchone as global_db_fetchone
    return global_db_fetchone(query, params)

def get_user_jid(room, nick):
    """الحصول على JID الحقيقي للمستخدم"""
    from run import get_user_jid as global_get_user_jid
    return global_get_user_jid(room, nick)

def acl_show(ttype, jid, nick, text):
    """عرض قائمة ACL"""
    room = extract_room_from_jid(jid)
    
    if not text or text == '%':
        acl_list = db_fetchall('SELECT * FROM acl WHERE room = ?', (room,))
    else:
        acl_list = db_fetchall('SELECT * FROM acl WHERE room = ? AND action LIKE ?', (room, text))
    
    if acl_list:
        msg = "📋 قائمة التحكم في الوصول (ACL):\n\n"
        for item in acl_list:
            action = item['action']
            condition = item['condition']
            value = item['value']
            command = item['command']
            level = item['level']
            expiry = item['expiry']
            
            if expiry:
                expiry_str = f" [ينتهي: {expiry}]"
            else:
                expiry_str = ""
            
            msg += f"• {action} {condition} '{value}' -> {command} (مستوى: {level}){expiry_str}\n"
    else:
        msg = "❌ لم يتم العثور على قواعد ACL"
    
    send_msg(ttype, jid, nick, msg)

def acl_add_del(ttype, jid, nick, text, flag):
    """إضافة أو حذف قاعدة ACL"""
    room = extract_room_from_jid(jid)
    user_level = get_user_permission_level(jid, nick, room)
    
    if user_level < 7:
        send_msg(ttype, jid, nick, "❌ ليس لديك الصلاحية الكافية لاستخدام هذا الأمر")
        return
    
    try:
        parts = text.split()
        if not parts:
            send_msg(ttype, jid, nick, "❌ يرجى إدخال المعاملات الصحيحة")
            return
        
        # معالجة الخيارات
        silent = False
        expiry = None
        level = 7  # مستوى افتراضي
        
        while parts and parts[0].startswith('/'):
            option = parts.pop(0)
            if option == '/صامت':
                silent = True
            elif option.startswith('/مدة'):
                try:
                    # معالجة المدة الزمنية
                    duration = option[4:]
                    if duration.endswith('s'):  # ثواني
                        expiry = int(time.time()) + int(duration[:-1])
                    elif duration.endswith('m'):  # دقائق
                        expiry = int(time.time()) + int(duration[:-1]) * 60
                    elif duration.endswith('h'):  # ساعات
                        expiry = int(time.time()) + int(duration[:-1]) * 3600
                    elif duration.endswith('d'):  # أيام
                        expiry = int(time.time()) + int(duration[:-1]) * 86400
                except:
                    send_msg(ttype, jid, nick, "❌ تنسيق الوقت غير صحيح")
                    return
        
        if not parts:
            send_msg(ttype, jid, nick, "❌ يرجى إدخال المعاملات الصحيحة")
            return
        
        # معالجة المستوى إذا كان أول عنصر رقم
        if parts[0].isdigit():
            level = int(parts[0])
            if level < 1 or level > 10:
                level = 7
            parts = parts[1:]
        
        if not parts:
            send_msg(ttype, jid, nick, "❌ يرجى إدخال المعاملات الصحيحة")
            return
        
        action = parts[0]
        if action not in acl_acts:
            send_msg(ttype, jid, nick, f"❌ الإجراء غير صحيح. الإجراءات المتاحة: {', '.join(acl_acts)}")
            return
        
        parts = parts[1:]
        if not parts:
            send_msg(ttype, jid, nick, "❌ يرجى إدخال الشرط والقيمة")
            return
        
        condition = parts[0]
        valid_conditions = ['=', '!=', 'sub', '!sub', 'exp', '!exp', 'cexp', '!cexp', '<', '>', '<=', '>=']
        if condition not in valid_conditions:
            send_msg(ttype, jid, nick, f"❌ الشرط غير صحيح. الشروط المتاحة: {', '.join(valid_conditions)}")
            return
        
        parts = parts[1:]
        if not parts:
            send_msg(ttype, jid, nick, "❌ يرجى إدخال القيمة")
            return
        
        value = parts[0]
        command = ' '.join(parts[1:]) if len(parts) > 1 else ''
        
        if flag and not command:
            send_msg(ttype, jid, nick, "❌ يرجى إدخال الأمر المراد تنفيذه")
            return
        
        # التحقق من وجود القاعدة
        existing = db_fetchone('SELECT * FROM acl WHERE room = ? AND action = ? AND condition = ? AND value = ? AND level = ?', 
                              (room, action, condition, value, level))
        
        if existing:
            # حذف القاعدة الموجودة
            db_execute('DELETE FROM acl WHERE room = ? AND action = ? AND condition = ? AND value = ? AND level = ?', 
                      (room, action, condition, value, level))
            msg = "✅ تم حذف القاعدة"
        else:
            if flag:
                # إضافة قاعدة جديدة
                db_execute('INSERT INTO acl (room, action, condition, value, command, level, expiry) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                          (room, action, condition, value, command, level, expiry))
                msg = "✅ تم إضافة القاعدة"
            else:
                msg = "❌ القاعدة غير موجودة"
        
        if not silent:
            expiry_str = f" [ينتهي: {expiry}]" if expiry else ""
            msg += f": {action} {condition} '{value}' -> '{command}' (مستوى: {level}){expiry_str}"
        
        send_msg(ttype, jid, nick, msg)
        
    except Exception as e:
        send_msg(ttype, jid, nick, f"❌ خطأ في معالجة الأمر: {str(e)}")

def acl_add(ttype, jid, nick, text):
    """إضافة قاعدة ACL"""
    return acl_add_del(ttype, jid, nick, text, True)

def acl_del(ttype, jid, nick, text):
    """حذف قاعدة ACL"""
    return acl_add_del(ttype, jid, nick, text, False)

def acl_clear(ttype, jid, nick, text):
    """مسح جميع قواعد ACL"""
    room = extract_room_from_jid(jid)
    user_level = get_user_permission_level(jid, nick, room)
    
    if user_level < 8:
        send_msg(ttype, jid, nick, "❌ ليس لديك الصلاحية الكافية لاستخدام هذا الأمر")
        return
    
    # حفظ نسخة احتياطية
    acl_backup = db_fetchall('SELECT * FROM acl WHERE room = ?', (room,))
    
    if acl_backup:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_data = json.dumps(acl_backup, ensure_ascii=False)
        # يمكن حفظها في ملف إذا لزم الأمر
    
    # مسح القواعد
    db_execute('DELETE FROM acl WHERE room = ?', (room,))
    
    send_msg(ttype, jid, nick, f"✅ تم مسح جميع قواعد ACL. تم حذف {len(acl_backup)} قاعدة")

def acl_handler(ttype, jid, nick, text):
    """معالج أوامر ACL الرئيسي"""
    if not text:
        send_msg(ttype, jid, nick, "📋 أوامر التحكم في الوصول (ACL):\n\n"
                                  "• !acl عرض - عرض جميع القواعد\n"
                                  "• !acl مسح - مسح جميع القواعد\n"
                                  "• !acl حذف [خيارات] إجراء شرط قيمة - حذف قاعدة\n"
                                  "• !acl [خيارات] [مستوى] إجراء شرط قيمة أمر - إضافة قاعدة\n\n"
                                  "🛠️ الخيارات:\n"
                                  "/صامت - عدم عرض التأكيد\n"
                                  "/مدةX - تعيين مدة انتهاء (X = 30s, 5m, 2h, 1d)\n\n"
                                  "📝 الإجراءات المتاحة:\n"
                                  "msg, prs, role, aff, nick, jid, jidfull, res, age, ver, vcard, all")
        return
    
    parts = text.split()
    command = parts[0]
    
    if command == 'عرض':
        acl_show(ttype, jid, nick, ' '.join(parts[1:]) if len(parts) > 1 else '%')
    elif command == 'مسح':
        acl_clear(ttype, jid, nick, ' '.join(parts[1:]))
    elif command == 'حذف':
        acl_del(ttype, jid, nick, ' '.join(parts[1:]))
    else:
        acl_add(ttype, jid, nick, text)

def acl_check_message(room, jid, nick, message_text):
    """فحص الرسائل ضد قواعد ACL"""
    try:
        acl_rules = db_fetchall('SELECT * FROM acl WHERE room = ? AND action = ?', (room, 'msg'))
        
        for rule in acl_rules:
            if acl_match_condition(message_text, rule['condition'], rule['value']):
                # تنفيذ الأمر المحدد
                acl_execute_command(room, jid, nick, rule['command'], message_text)
                return True
                
        return False
    except Exception as e:
        print(f"❌ خطأ في فحص ACL للرسائل: {e}")
        return False

def acl_check_presence(room, jid, nick, presence_type, status, affiliation, role):
    """فحص الحضور ضد قواعد ACL"""
    try:
        acl_rules = db_fetchall('SELECT * FROM acl WHERE room = ? AND action IN (?, ?, ?, ?)', 
                               (room, 'prs', 'role', 'aff', 'all'))
        
        for rule in acl_rules:
            matched = False
            value_to_check = ""
            
            if rule['action'] == 'prs':
                value_to_check = status or ''
            elif rule['action'] == 'role':
                value_to_check = role or ''
            elif rule['action'] == 'aff':
                value_to_check = affiliation or ''
            elif rule['action'] == 'all':
                value_to_check = f"{jid}|{nick}|{status}|{role}|{affiliation}"
            
            if acl_match_condition(value_to_check, rule['condition'], rule['value']):
                acl_execute_command(room, jid, nick, rule['command'], None)
                matched = True
                
        return matched
    except Exception as e:
        print(f"❌ خطأ في فحص ACL للحضور: {e}")
        return False

def acl_match_condition(actual_value, condition, expected_value):
    """مطابقة القيمة مع الشرط"""
    if actual_value is None:
        actual_value = ""
    
    actual_value = safe_decode(actual_value)
    expected_value = safe_decode(expected_value)
    
    try:
        if condition == '=':
            return actual_value.lower() == expected_value.lower()
        elif condition == '!=':
            return actual_value.lower() != expected_value.lower()
        elif condition == 'sub':
            return expected_value.lower() in actual_value.lower()
        elif condition == '!sub':
            return expected_value.lower() not in actual_value.lower()
        elif condition == 'exp':
            return bool(re.search(expected_value, actual_value, re.IGNORECASE))
        elif condition == '!exp':
            return not bool(re.search(expected_value, actual_value, re.IGNORECASE))
        elif condition == 'cexp':
            return bool(re.search(expected_value, actual_value))
        elif condition == '!cexp':
            return not bool(re.search(expected_value, actual_value))
        elif condition in ['<', '>', '<=', '>=']:
            # للمقارنة العددية (مفيد مع العمر)
            try:
                actual_num = int(actual_value)
                expected_num = int(expected_value)
                
                if condition == '<':
                    return actual_num < expected_num
                elif condition == '>':
                    return actual_num > expected_num
                elif condition == '<=':
                    return actual_num <= expected_num
                elif condition == '>=':
                    return actual_num >= expected_num
            except:
                return False
    except Exception as e:
        print(f"❌ خطأ في مطابقة الشرط: {e}")
    
    return False

def acl_execute_command(room, jid, nick, command, message_text):
    """تنفيذ الأمر المحدد في قاعدة ACL"""
    try:
        if not command:
            return
        
        # استبدال المتغيرات
        command = command.replace('${NICK}', nick)
        command = command.replace('${JID}', jid)
        command = command.replace('${ROOM}', room)
        
        if message_text and '${TEXT}' in command:
            command = command.replace('${TEXT}', message_text)
        
        # إذا كان الأمر يبدأ بـ !، نعالجه كأمر عادي
        if command.startswith('!'):
            from run import process_command
            process_command('groupchat', f"{room}/{nick}", nick, command[1:])
        else:
            # إرسال الرسالة كما هي
            send_msg('groupchat', room, nick, command)
            
    except Exception as e:
        print(f"❌ خطأ في تنفيذ أمر ACL: {e}")

def handle_message_acl(conn, message):
    """معالج ACL للرسائل - يمكن استدعاؤها من run.py"""
    try:
        from_jid = str(message.getFrom())
        body = message.getBody()
        msg_type = message.getType()
        
        if msg_type != 'groupchat' or not body:
            return
        
        if '/' in from_jid:
            room, nick = from_jid.split('/', 1)
            acl_check_message(room, from_jid, nick, body)
                
    except Exception as e:
        print(f"❌ خطأ في معالج ACL للرسائل: {e}")

def handle_presence_acl(conn, presence):
    """معالج ACL للحضور - يمكن استدعاؤها من run.py"""
    try:
        from_jid = str(presence.getFrom())
        presence_type = presence.getType()
        
        if presence_type == 'unavailable' or not from_jid or '/' not in from_jid:
            return
        
        room, nick = from_jid.split('/', 1)
        
        # استخراج معلومات الحضور
        status = ''
        affiliation = 'none'
        role = 'none'
        
        x_tag = presence.getTag('x', namespace='http://jabber.org/protocol/muc#user')
        if x_tag:
            item_tag = x_tag.getTag('item')
            if item_tag:
                affiliation = safe_decode(item_tag.getAttr('affiliation') or 'none')
                role = safe_decode(item_tag.getAttr('role') or 'none')
        
        status_tag = presence.getTag('status')
        if status_tag:
            status = safe_decode(status_tag.getData() or '')
        
        acl_check_presence(room, from_jid, nick, presence_type, status, affiliation, role)
                
    except Exception as e:
        print(f"❌ خطأ في معالج ACL للحضور: {e}")

def execute():
    """تسجيل أوامر البلجن"""
    commands = [
        (7, 'acl', acl_handler, 0, 'نظام التحكم في الوصول - ACL: !acl [عرض/مسح/حذف/إضافة]'),
        (7, 'صلاحيات', acl_handler, 0, 'نظام التحكم في الوصول - مرادف لـ !acl'),
    ]
    
    return commands

# دوال يمكن استدعاؤها من run.py الرئيسي
def get_message_handlers():
    """إرجاع معالجات الرسائل"""
    return [handle_message_acl]

def get_presence_handlers():
    """إرجاع معالجات الحضور"""
    return [handle_presence_acl]

def get_iq_handlers():
    """إرجاع معالجات IQ"""
    return []

def get_timer_functions():
    """إرجاع دوال المؤقت"""
    return []

def init_plugin(global_vars):
    """تهيئة البلجن بالمتغيرات العالمية"""
    # يمكن استخدام هذه الدالة لتهيئة المتغيرات إذا لزم الأمر
    print("✅ تم تحميل بلجن نظام التحكم في الوصول (ACL)")